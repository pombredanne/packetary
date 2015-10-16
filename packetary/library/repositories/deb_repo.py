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
from debian import deb822
from debian import debian_support
import gzip
import os
import six

from packetary.library import package
from packetary.library.gzip_stream import GzipDecompress

from .base import IndexWriter
from .base import logger
from .base import RepositoryWithIndex


_OPERATORS = {
    '>>': 'gt',
    '<<': 'lt',
    '=': 'eq',
    '>=': 'ge',
    '<=': 'le',
}

_ARCH_MAPPING = {
    'amd64': 'x86_64',
    'i386': 'i386',
    'all': '*',
    'x86_64': 'amd64',
}

_Version = debian_support.Version


def _get_version_range(rel_version):
    if rel_version is None:
        return package.VersionRange()
    return package.VersionRange(
        _OPERATORS[rel_version[0]],
        rel_version[1],
    )


class DebPackage(package.Package):
    """Debian package."""

    def __init__(self, base_url, repo, dpkg):
        self.base_url = base_url
        self.repo = repo
        self.dpkg = dpkg
        self._version = _Version(dpkg['version'])
        self._size = int(dpkg['size'])

    @property
    def name(self):
        return self.dpkg['package']

    @property
    def version(self):
        return self._version

    @property
    def size(self):
        return self._size

    @property
    def checksum(self):
        if 'sha1' in self.dpkg:
            return 'sha1', self.dpkg['sha1']
        if 'MD5sum' in self.dpkg:
            return 'md5', self.dpkg['MD5sum']
        return None, None

    @property
    def filename(self):
        return self.dpkg["Filename"]

    @property
    def url(self):
        return self.base_url + "/../" + self.dpkg["Filename"]

    @property
    def requires(self):
        return self._get_relations('depends')

    @property
    def provides(self):
        return self._get_relations('provides')

    @property
    def obsoletes(self):
        return self._get_relations('replaces')

    def _get_relations(self, name):
        if hasattr(self, '_' + name):
            return getattr(self, '_' + name)

        relations = list()
        for variants in self.dpkg.relations[name]:
            choice = None
            for v in reversed(variants):
                choice = package.Relation(
                    v['name'],
                    _get_version_range(v.get('version')),
                    choice
                )

            if choice is not None:
                relations.append(choice)

        setattr(self, '_' + name, relations)
        return relations


class DebIndexWriter(IndexWriter):
    def __init__(self, context, destination):
        self.context = context
        self.destination = destination
        self.index = defaultdict(FastRBTree)

    def add(self, p):
        self.index[p.repo][p] = None

    def flush(self):
        with self.context.get_execution_scope(0) as scope:
            for repo, packages in six.iteritems(self.index):
                scope.execute(
                    self._update_index,
                    self.destination, repo, packages
                )

    @staticmethod
    def _update_index(destination, repo, packages):
        """Saves the index file in local file system."""
        path = os.path.join(destination, "dists", *repo)
        index_file = os.path.join(path, "Packages.gz")
        logger.info("the index file: %s.", index_file)
        tmp = os.path.join(path, "Packages.tmp.gz")
        if os.path.exists(index_file):
            logger.info("update existing index: %s", index_file)
            with gzip.open(index_file, "rb") as stream:
                pkg_iter = deb822.Packages.iter_paragraphs(stream)
                for dpkg in pkg_iter:
                    packages.insert(
                        DebPackage(destination, repo, dpkg), None
                    )
        if not os.path.exists(path):
            os.makedirs(path)

        with gzip.open(tmp, "wb") as index:
            for p in packages.keys():
                p.dpkg.dump(fd=index)
                index.write('\n')
        os.rename(tmp, index_file)
        logger.info(
            "the index %s has been updated successfully.", index_file
        )


class DebRepository(RepositoryWithIndex):
    def __init__(self, context, arch):
        super(DebRepository, self).__init__(
            context, 'binary-' + _ARCH_MAPPING[arch]
        )

    def get_package_path(self, p):
        return p.filename.split("/")

    def create_index_writer(self, destination):
        return DebIndexWriter(self.context, destination)

    def parse_urls(self, urls):
        """Returns the url-components"""
        for url in urls:
            try:
                baseurl, suite, comps = url.split(" ", 2)
            except ValueError:
                raise ValueError(
                    "invalid url: {0}\n"
                    "expected: baseurl suite component[ component]"
                    .format(url)
                )

            if baseurl.endswith("/"):
                baseurl = baseurl[:-1]

            for comp in comps.split(":"):
                yield baseurl, (suite, comp, self.arch)

    def load_packages(self, url, consumer):
        """Loads from Packages.gz."""
        baseurl, repo = url

        index_file = "{0}/{1}/{2}/{3}/Packages.gz".format(baseurl, *repo)
        logger.info("loading packages from: %s", index_file)
        with self.context.connections.acquire() as connection:
            stream = GzipDecompress(connection.open_stream(index_file))
            pkg_iter = deb822.Packages.iter_paragraphs(stream)
            for dpkg in pkg_iter:
                consumer(DebPackage(baseurl, repo, dpkg))
        logger.info(
            "packages from %s has been loaded successfully.", index_file
        )
