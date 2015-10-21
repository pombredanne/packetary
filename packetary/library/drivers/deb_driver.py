#    Copyright 2015 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from bintrees import FastRBTree
from collections import defaultdict
from contextlib import closing
from datetime import datetime
from debian import deb822
import fcntl
import gzip
import logging
import os
import six

from packetary.library import checksum
from packetary.library.driver import IndexWriter
from packetary.library.driver import RepoDriver
from packetary.library.drivers.deb_package import DebPackage
from packetary.library.streams import GzipDecompress


logger = logging.getLogger(__package__)


_ARCH_MAPPING = {
    'i386': 'i386',
    'x86_64': 'amd64',
}

_SPACE_COUNT_IN_META = 17

_CHECK_SUMS = [
    ("MD5Sum", checksum.md5),
    ("SHA1", checksum.sha1),
    ("SHA256", checksum.sha256)
]

_DEFAULT_ORIGIN = "Unknown"


class DebIndexWriter(IndexWriter):
    def __init__(self, driver, destination):
        self.driver = driver
        self.destination = os.path.abspath(destination)
        self.index = defaultdict(FastRBTree)
        self.origin = None

    def add(self, p):
        self.index[(p.suite, p.comp)][p] = None
        if self.origin is None:
            self.origin = p.dpkg.get('origin')

    def flush(self, keep_existing=True):
        suites = set()
        self.origin = self.origin or _DEFAULT_ORIGIN
        for repo, packages in six.iteritems(self.index):
            self._rebuild_index(repo, packages, keep_existing)
            suites.add(repo[0])
        self._updates_global_releases(suites)

    def _rebuild_index(self, repo, packages, keep_existing):
        """Saves the index file in local file system."""
        path = os.path.join(
            self.destination, "dists", repo[0], repo[1],
            "binary-" + self.driver.arch
        )
        index_file = os.path.join(path, "Packages.gz")
        logger.info("the index file: %s.", index_file)
        tmp = os.path.join(path, "Packages.tmp.gz")
        dirty_files = set()
        if keep_existing:
            on_existing_package = lambda x: packages.insert(p, None)
            handler = lambda x: None
        else:
            on_existing_package = lambda x: dirty_files.add(x.filename)
            handler = lambda x: dirty_files.discard(x.filename)

        if os.path.exists(index_file):
            logger.info("process existing index: %s", index_file)
            self.driver.load(self.destination, repo, on_existing_package)

        if not os.path.exists(path):
            os.makedirs(path)

        with closing(gzip.open(tmp, "wb")) as index:
            for p in packages.keys():
                p.dpkg.dump(fd=index)
                index.write(b"\n")
                handler(p)

        os.rename(tmp, index_file)
        for f in dirty_files:
            os.remove(os.path.join(self.destination, f))
            logger.info("File %s was removed.", f)

        self._generate_component_release(path, *repo)

        logger.info(
            "the index %s has been updated successfully.", index_file
        )

    def _generate_component_release(self, path, suite, component):
        """Generates the release meta information."""
        meta_filename = os.path.join(path, "Release")
        with closing(open(meta_filename + ".tmp", "w")) as meta:
            self._dump_meta(meta, {
                "Active": suite,
                "Component": component,
                "Origin": self.origin,
                "Label": self.origin,
                "Architecture": self.driver.arch
            })
        os.rename(meta_filename + ".tmp", meta_filename)

    def _updates_global_releases(self, suites):
        """Generates the overall meta information."""
        path = os.path.join(self.destination, "dists")
        date_str = six.text_type(datetime.utcnow())
        for suite in suites:
            suite_dir = os.path.join(path, suite)
            components = [
                d for d in os.listdir(suite_dir)
                if os.path.isdir(os.path.join(suite_dir, d))
            ]
            release_file = os.path.join(suite_dir, "Release")
            with closing(open(release_file, "w")) as meta:
                fcntl.flock(meta.fileno(), fcntl.LOCK_EX)
                try:
                    self._dump_meta(meta, {
                        "Origin": self.origin,
                        "Label": self.origin,
                        "Suite": suite,
                        "Codename": suite,
                        "Architecture": self.driver.arch,
                        "Components": " ".join(components),
                        "Date": date_str,
                        "Description": "{0} {1} Partial".format(
                            self.origin, suite
                        ),
                    })
                    self._dump_files(meta, suite_dir, components)
                finally:
                    fcntl.flock(meta.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _dump_files(meta, suite_dir, components):
        """Dumps files meta information."""
        for d in components:
            comp_path = os.path.join(suite_dir, d)
            for hash_name, hash_method in _CHECK_SUMS:
                meta.write(":".join((hash_name, "\n")))
                for root, dirs, files in os.walk(comp_path):
                    for f in files:
                        filepath = os.path.join(root, f)
                        with closing(open(filepath, "rb")) as fobj:
                            meta.write(hash_method(fobj))
                            size_str = six.text_type(
                                os.fstat(fobj.fileno()).st_size
                            )
                            meta.write(
                                " " * (_SPACE_COUNT_IN_META - len(size_str))
                            )
                            meta.write(size_str)
                            meta.write(" ")
                            meta.write(filepath[len(suite_dir) + 1:])
                            meta.write("\n")

    @staticmethod
    def _dump_meta(stream, meta):
        for k, v in six.iteritems(meta):
            stream.write("".join((k, ": ", v, "\n")))

    @staticmethod
    def _is_meta_file(n):
            return n.startswith("Release") or n.startswith("Packages")


class Driver(RepoDriver):
    """Driver for deb repositories."""

    def __init__(self, context, arch):
        self.connections = context.connections
        self.arch = _ARCH_MAPPING[arch]

    def create_index(self, destination):
        return DebIndexWriter(self, destination)

    def parse_urls(self, urls):
        for url in urls:
            try:
                baseurl, suite, comps = url.split(" ", 2)
            except ValueError:
                raise ValueError(
                    "Invalid url: {0}\n"
                    "Expected: baseurl suite component[ component]"
                    .format(url)
                )

            if baseurl.endswith("/dists/"):
                baseurl = baseurl[:-7]
            elif baseurl.endswith("/dists"):
                baseurl = baseurl[:-6]
            elif baseurl.endswith("/"):
                baseurl = baseurl[:-1]

            for comp in comps.split(":"):
                yield baseurl, (suite, comp)

    def get_path(self, base, package):
        baseurl = base or package.baseurl
        return "/".join((baseurl, package.filename))

    def load(self, baseurl, repo, consumer):
        """Loads from Packages.gz."""
        suite, comp = repo
        index_file = "{0}/dists/{1}/{2}/binary-{3}/Packages.gz".format(
            baseurl, suite, comp, self.arch
        )
        logger.info("loading packages from: %s", index_file)
        with self.connections.get() as connection:
            stream = GzipDecompress(connection.open_stream(index_file))
            pkg_iter = deb822.Packages.iter_paragraphs(stream)
            for dpkg in pkg_iter:
                consumer(DebPackage(dpkg, baseurl, suite, comp))

        logger.info(
            "packages from %s has been loaded successfully.", index_file
        )
