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
import os
import six

from packetary.library.constants import byte_lf
from packetary.library.streams import GzipDecompress

from .base import IndexWriter
from .base import logger
from .base import BaseRepoDriver
from .deb_package import DebPackage


_ARCH_MAPPING = {
    'amd64': 'x86_64',
    'i386': 'i386',
    'all': '*',
    'x86_64': 'amd64',
}


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
            with closing(gzip.open(index_file, "rb")) as stream:
                pkg_iter = deb822.Packages.iter_paragraphs(stream)
                for dpkg in pkg_iter:
                    packages.insert(
                        DebPackage(dpkg, destination, repo), None
                    )
        if not os.path.exists(path):
            os.makedirs(path)

        with closing(gzip.open(tmp, "wb")) as index:
            for p in packages.keys():
                p.dpkg.dump(fd=index)
                index.write(byte_lf)
        os.rename(tmp, index_file)
        logger.info(
            "the index %s has been updated successfully.", index_file
        )


class DebRepoDriver(BaseRepoDriver):
    def __init__(self, context, arch):
        super(DebRepoDriver, self).__init__(
            context, 'binary-' + _ARCH_MAPPING[arch]
        )

    def get_package_dir(self, package):
        return []

    def create_index_writer(self, destination):
        return DebIndexWriter(self.context, destination)

    def url_iterator(self, urls):
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
                baseurl = baseurl[:-6]
            elif baseurl.endswith("/dists"):
                baseurl = baseurl[:-5]
            elif baseurl.endswith("/"):
                baseurl = baseurl[:-1]

            for comp in comps.split(":"):
                yield baseurl, (suite, comp, self.arch)

    def load_packages(self, url, consumer):
        """Loads from Packages.gz."""
        baseurl, repo = url

        index_file = "{0}/dists/{1}/{2}/{3}/Packages.gz".format(baseurl, *repo)
        logger.info("loading packages from: %s", index_file)
        with self.context.connections.acquire() as connection:
            stream = GzipDecompress(connection.open_stream(index_file))
            pkg_iter = deb822.Packages.iter_paragraphs(stream)
            for dpkg in pkg_iter:
                consumer(DebPackage(dpkg, baseurl + "/", repo))
        logger.info(
            "packages from %s has been loaded successfully.", index_file
        )
