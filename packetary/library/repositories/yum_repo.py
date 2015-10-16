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

import lxml.etree as etree
import os
import six
import six.moves.urllib.parse as urlparse
import subprocess

from packetary.library.packages import YumPackage
from packetary.library.gzip_stream import GzipDecompress

from .base import IndexWriter
from .base import logger
from .base import RepositoryWithIndex


_namespaces = {
    "main": "http://linux.duke.edu/metadata/common",
    "md": "http://linux.duke.edu/metadata/repo"
}


def _find_createrepo():
    """Finds the createrepo executable"""
    paths = os.environ['PATH'].split(os.pathsep)
    createrepo = os.environ.get("CREATEREPO_PATH", "createrepo")
    if not os.path.isfile(createrepo):
        for p in paths:
            f = os.path.join(p, createrepo)
            if os.path.isfile(f):
                return f
        return None
    else:
        return createrepo


createrepo = _find_createrepo()


class YumIndexWriter(IndexWriter):
    def __init__(self, context, destination):
        self.context = context
        self.destination = destination
        self.repos = set()

    def add(self, p):
        self.repos.add(p.repo)

    def flush(self):
        if createrepo is None:
            six.print_(
                "Please install createrepo utility and run the following "
                "commands manually:"
            )

        with self.context.get_execution_scope(0) as scope:
            for repo in self.repos:
                self._createrepo(scope, repo)

    def _createrepo(self, scope, repo):
        path = os.path.join(self.destination, *repo)
        if os.path.exists(os.path.join(path, "repodata", "repomd.xml")):
            cmd = [createrepo, path, "--update"]
        else:
            cmd = [createrepo, path]
        if createrepo is not None:
            scope.execute(subprocess.check_call, cmd)
        else:
            cmd[0] = "createrepo"
            six.print_(">>", subprocess.list2cmdline(cmd))


class YumRepository(RepositoryWithIndex):
    """Yum repositories implementation"""

    def get_package_path(self, p):
        return list(p.repo) + p.filename.split("/")

    def create_index_writer(self, destination):
        return YumIndexWriter(self.context, destination)

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
