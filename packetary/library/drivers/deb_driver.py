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

from __future__ import with_statement

from bintrees import FastRBTree
from collections import defaultdict
from contextlib import closing
from debian import deb822
import gzip
import logging
import os
import six

from packetary.library.constants import byte_lf
from packetary.library.driver import IndexWriter
from packetary.library.driver import RepoDriver
from packetary.library.drivers.deb_package import DebPackage
from packetary.library.streams import GzipDecompress


logger = logging.getLogger(__package__)


_ARCH_MAPPING = {
    'i386': 'binary-i386',
    'x86_64': 'binary-amd64',
}


class DebIndexWriter(IndexWriter):
    def __init__(self, driver, destination):
        self.driver = driver
        self.destination = os.path.abspath(destination)
        self.index = defaultdict(FastRBTree)

    def add(self, p):
        self.index[p.reponame][p] = None

    def flush(self, keep_existing=True):
        for repo, packages in six.iteritems(self.index):
            self._rebuild_index(repo, packages, keep_existing)

    def _rebuild_index(self, reponame, packages, keep_existing):
        """Saves the index file in local file system."""
        path = os.path.join(
            self.destination, "dists", reponame, self.driver.arch
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
            self.driver.load(self.destination, reponame, on_existing_package)

        if not os.path.exists(path):
            os.makedirs(path)

        with closing(gzip.open(tmp, "wb")) as index:
            for p in packages.keys():
                p.dpkg.dump(fd=index)
                index.write(byte_lf)
                handler(p)

        os.rename(tmp, index_file)
        for f in dirty_files:
            os.remove(os.path.join(self.destination, f))
            logger.info("File %s was removed.", f)

        logger.info(
            "the index %s has been updated successfully.", index_file
        )


class DebRepoDriver(RepoDriver):
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
                    "invalid url: {0}\n"
                    "expected: baseurl suite component[ component]"
                    .format(url)
                )

            if baseurl.endswith("/dists/"):
                baseurl = baseurl[:-7]
            elif baseurl.endswith("/dists"):
                baseurl = baseurl[:-6]
            elif baseurl.endswith("/"):
                baseurl = baseurl[:-1]

            for comp in comps.split(":"):
                yield baseurl, "/".join((suite, comp))

    def get_path(self, base, package):
        baseurl = base or package.origin
        return "/".join((baseurl, package.filename))

    def load(self, baseurl, reponame, consumer):
        """Loads from Packages.gz."""
        index_file = "{0}/dists/{1}/{2}/Packages.gz".format(
            baseurl, reponame, self.arch
        )
        logger.info("loading packages from: %s", index_file)
        with self.connections.acquire() as connection:
            stream = GzipDecompress(connection.open_stream(index_file))
            pkg_iter = deb822.Packages.iter_paragraphs(stream)
            for dpkg in pkg_iter:
                consumer(DebPackage(dpkg, baseurl, reponame))

        logger.info(
            "packages from %s has been loaded successfully.", index_file
        )
