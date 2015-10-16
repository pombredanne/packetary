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

from collections import defaultdict
import lxml.etree as etree
import os
import six
import six.moves.urllib.parse as urlparse

from packetary.library.packages import YumPackage
from packetary.library.gzip_stream import GzipDecompress

from .base import IndexWriter
from .base import logger
from .base import RepositoryWithIndex


_namespaces = {
    "main": "http://linux.duke.edu/metadata/common",
    "md": "http://linux.duke.edu/metadata/repo"
}


class YumIndexWriter(IndexWriter):
    def __init__(self, repo, destination):
        self.repo = repo
        self.destination = destination
        self.index = defaultdict(list)

    def add(self, p):
        self.index[p.repo].append(p)

    def flush(self):
        for k in six.iterkeys(self.index):
            cmd = "createmirror --target {0}".format(
                os.path.join(self.destination, *k)
            )
            print cmd


class YumRepository(RepositoryWithIndex):
    """Yum repositories implementation"""

    def get_package_path(self, p):
        return list(p.repo) + p.filename.split("/")

    def create_index_writer(self, destination):
        return YumIndexWriter(self, destination)

    def parse_urls(self, urls):
        for url in urls:
            if url.endswith("/"):
                url = url[:-1]
            yield "/".join((url, self.arch, ""))

    def load_packages(self, baseurl, consumer):
        """Reads packages from metdata."""
        repomd = baseurl + "/repodata/repomd.xml"
        logger.debug("repomd: %s", repomd)

        nodes = None
        with self.context.connections.acquire() as connection:
            repomd_tree = etree.parse(connection.open_stream(repomd))

            node = repomd_tree.find("./md:data[@type='primary']", _namespaces)
            if node is None:
                raise ValueError("malformed meta: %s" % repomd)
            location = node.find("./md:location", _namespaces).attrib["href"]

            stream = GzipDecompress(connection.open_stream(
                urlparse.urljoin(baseurl, location)
            ))
            nodes = etree.parse(stream)

        for pkg_tag in nodes.iterfind("./main:package", _namespaces):
            consumer(YumPackage(
                pkg_tag,
                baseurl
            ))
