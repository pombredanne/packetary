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

from collections import namedtuple
import lxml.etree as etree
import six

from packetary.library import package
from packetary.library.gzip_stream import GzipDecompress

from .base import logger
from .base import RepositoryWithIndex


_PackageVersion = namedtuple("_PackageVersion", ("epoch", "version", "release"))


class PackageVersion(_PackageVersion):
    def __new__(cls, args):
        return _PackageVersion.__new__(
            cls,
            int(args.get("epoch", 0)),
            tuple(args.get("ver", "0.0").split(".")),
            tuple(args.get("rel", "0").split('.'))
        )

    def __str__(self):
        return "%s-%s-%s" % (
            self.epoch, ".".join(self.version), ".".join(self.release)
        )


def _get_version_range(args):
    if "flags" not in args:
        return package.VersionRange()
    return package.VersionRange(
        args["flags"].lower(),
        PackageVersion(args)
    )


_common_ns = "http://linux.duke.edu/metadata/common"
_filelist_ns = "http://linux.duke.edu/metadata/filelists"
_other_ns = "http://linux.duke.edu/metadata/other"
_repo_ns = "http://linux.duke.edu/metadata/repo"
_rpm_ns = "http://linux.duke.edu/metadata/rpm"

_primary_package_sel = "{http://linux.duke.edu/metadata/common}package"
_filelist_package_sel = "{http://linux.duke.edu/metadata/filelists}package"
_other_package_sel = "{http://linux.duke.edu/metadata/other}package"
_package_id_sel = '{http://linux.duke.edu/metadata/common}checksum[@pkgid="YES"]'
_primary_db = "{http://linux.duke.edu/metadata/common}package"
_filelists_db = "{http://linux.duke.edu/metadata/filelists}package"
_others_db = "{http://linux.duke.edu/metadata/other}package"
_db_pattern = "{http://linux.duke.edu/metadata/repo}data[@type='%s']"
_location_sel = "{http://linux.duke.edu/metadata/repo}location"

_primary_namespaces = {
    "p": _common_ns,
    "rpm": _rpm_ns
}


class YumPackage(package.Package):
    """Yum package."""
    def __init__(self, baseurl, pkg, files, other):
        self.base_url = baseurl
        self.pkg = pkg
        self.files = files
        self.other = other
        self._name = self._find_tag("./p:name").text
        self._version = PackageVersion(self._find_tag("./p:version").attrib)
        self._size = int(self._find_tag("./p:size").attrib.get("package"))

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def size(self):
        return self._size

    @property
    def checksum(self):
        checksum = self._find_tag("./p:checksum")
        return checksum.attrib["type"], checksum.text

    @property
    def filename(self):
        return self._find_tag("./p:location").attrib["href"]

    @property
    def url(self):
        return "/".join((self.base_url, self.filename))

    @property
    def requires(self):
        return self._get_relations('requires')

    @property
    def provides(self):
        return self._get_relations('provides')

    @property
    def obsoletes(self):
        return self._get_relations('obsoletes')

    def _find_tag(self, path):
        return self.pkg.find(path, namespaces=_primary_namespaces)

    def _iter_tag(self, path):
        return self.pkg.iterfind(path, namespaces=_primary_namespaces)

    def _get_relations(self, name):
        if hasattr(self, '_' + name):
            return getattr(self, '_' + name)

        relations = list()
        for elem in self._iter_tag("./p:format/rpm:%s/rpm:entry" % name):
            rel = package.Relation(
                elem.attrib['name'],
                _get_version_range(elem.attrib)
            )
            relations.append(rel)

        setattr(self, '_' + name, relations)
        return relations


class YumRepository(RepositoryWithIndex):
    def create_index_writer(self, destination):
        raise NotImplementedError

    def parse_urls(self, urls):
        for url in urls:
            if url.endswith("/"):
                url = url[:-1]
            yield "/".join((url, self.arch, ""))

    def load_packages(self, baseurl, consumer):
        """Reads packages from metdata."""
        repomd = baseurl + "repodata/repomd.xml"
        logger.debug("repomd: %s", repomd)
        with self.context.connections.acquire() as connection:
            repomd_tree = etree.parse(connection.open_stream(repomd))

        primary = dict()
        filelist = dict()
        other = dict()

        handlers = [
            ("primary", primary, _common_ns, self._find_package_id),
            ("filelists", filelist, _filelist_ns, self._get_package_id),
            ("other", other, _other_ns, self._get_package_id)
        ]

        namespaces = {"md": _repo_ns}
        with self.context.get_execution_scope() as scope:
            for kind, dictionary, ns, get_id in handlers:
                # "{http://linux.duke.edu/metadata/repo}data[@type='%s']"
                node = repomd_tree.find(
                    "./md:data[@type='%s']" % kind, namespaces
                )
                if node is None:
                    logger.warning("tag '%s' not found.", kind)
                    continue

                location = node.find("./md:location", namespaces).attrib["href"]
                scope.execute(
                    self._read_meta,
                    self.context.connections,
                    baseurl + location, dictionary, ns, get_id
                )

        for pkgid, pkg in six.iteritems(primary):
            consumer(YumPackage(
                baseurl,
                pkg,
                filelist.get(pkgid),
                other.get(pkgid)
            ))

    @staticmethod
    def _read_meta(connections, location, dictionary, ns, get_id):
        # parse primary XML
        with connections.acquire() as connection:
            stream = GzipDecompress(connection.open_stream(location))
            tree = etree.parse(stream)

        # read package nodes
        for pkg_node in tree.iterfind("./md:package", {"md": ns}):
            dictionary[get_id(pkg_node)] = pkg_node

    @staticmethod
    def _find_package_id(node):
        return node.find(
            './p:checksum[@pkgid="YES"]', namespaces=_primary_namespaces
        ).text

    @staticmethod
    def _get_package_id(node):
        return node.attrib['pkgid']
