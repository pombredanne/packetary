# -*- coding: utf-8 -*-

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

from contextlib import closing
import copy
import datetime
import fcntl
import errno
import gzip
import os

from debian import deb822
from debian import debfile
from debian.debian_support import Version
import six

from packetary.drivers.base import RepositoryDriver
from packetary.library.checksum import composite as checksum_composite
from packetary.library.streams import GzipDecompress
from packetary.objects import FileChecksum
from packetary.objects import Package
from packetary.objects import PackageRelation
from packetary.objects import Repository
from packetary.objects import VersionRange


_OPERATORS_MAPPING = {
    '>>': 'gt',
    '<<': 'lt',
    '=': 'eq',
    '>=': 'ge',
    '<=': 'le',
}

_ARCHITECTURE_MAPPING = {
    "x86_64": "amd64",
    "i386": "i386",
    "source": "Source",
    "amd64": "x86_64",
}

_PRIORITIES = {
    "required": 1,
    "important": 2,
    "standard": 3,
    "optional": 4,
    "extra": 5
}

# Order is important
_REPOSITORY_FILES = [
    "Packages",
    "Release",
    "Packages.gz"
]

_MANDATORY_PRIORITY = 3

_CHECKSUM_METHODS = (
    "MD5Sum",
    "SHA1",
    "SHA256"
)

_checksum_collector = checksum_composite('md5', 'sha1', 'sha256')


class DebRepositoryDriver(RepositoryDriver):
    def parse_urls(self, urls):
        """Parses the repository url.
        :return: the sequence of parsed urls
        """
        for url in urls:
            base, suite, components = url.split(" ", 2)
            if base.endswith("dists/"):
                base = base[:-7]
            elif base.endswith("dists"):
                base = base[:-6]
            elif base.endswith("/"):
                base = base[:-1]
            for component in components.split():
                yield (base, suite, component)

    def get_repository(self, parsed_url, arch, consumer):
        """Loads one repository information."""
        base, suite, component = parsed_url
        release = "/".join((
            base, "dists", suite, component,
            "binary-" + _ARCHITECTURE_MAPPING[arch],
            "Release"
        ))
        deb_release = deb822.Release(self.connection.open_stream(release))
        consumer(Repository(
            name=(deb_release["Archive"], deb_release["Component"]),
            architecture=_ARCHITECTURE_MAPPING[deb_release["Architecture"]],
            origin=deb_release["origin"],
            url=base + "/"
        ))

    def get_packages(self, repository, consumer):
        """Loads packages from repository.
        :param repository: the repository object
        :param consumer: the package consumer
        """
        index = _get_meta_url(repository, "Packages.gz")
        stream = GzipDecompress(self.connection.open_stream(index))
        self.logger.info("loading packages from %s ...", index)
        pkg_iter = deb822.Packages.iter_paragraphs(stream)
        counter = 0
        for dpkg in pkg_iter:
            try:
                consumer(Package(
                    repository=repository,
                    name=dpkg["package"],
                    version=Version(dpkg['version']),
                    filesize=int(dpkg.get('size', -1)),
                    filename=dpkg["filename"],
                    checksum=FileChecksum(
                        md5=dpkg.get("md5sum"),
                        sha1=dpkg.get("sha1"),
                        sha256=dpkg.get("sha256"),
                    ),
                    mandatory=_is_mandatory(dpkg),
                    requires=_get_relations(dpkg, "depends", "pre-depends"),
                    obsoletes=_get_relations(dpkg, "replaces"),
                    provides=_get_relations(dpkg, "provides"),
                ))
            except KeyError:
                self.logger.error("Malformed index: %s - %s", repository, dpkg.get_as_string())
                raise
            counter += 1

        self.logger.info("loaded: %d packages from %s.", counter, index)

    def save_packages(self, repository, packages):
        """Assigns new packages to repository.
        :param repository: the target repository
        :param packages: the set of packages
        """
        path = _get_meta_path(repository, "")
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        index = os.path.join(path, "Packages")
        index_gz = os.path.join(path, "Packages.gz")
        origin = "Origin: {0}\n".format(repository.origin).encode("utf8")
        count = 0
        with closing(open(index, "wb")) as fd1:
            with closing(gzip.open(index_gz, "wb")) as fd2:
                writer = _composite_writer(fd1, fd2)
                for pkg in packages:
                    filename = os.path.join(repository.url, pkg.filename)
                    with closing(debfile.DebFile(filename)) as deb:
                        content = deb.control.get_content(debfile.CONTROL_FILE)
                    writer(content)
                    writer(origin)
                    writer("Size: {0}\n".format(pkg.filesize))
                    writer("Filename: {0}\n".format(pkg.filename))
                    for k, v in six.moves.zip(_CHECKSUM_METHODS, pkg.checksum):
                        writer("{0}: {1}\n".format(k, v))
                    writer("\n")
                    count += 1
        self.logger.info("saved %d packages in %s", count, repository)
        self._update_main_index(repository)

    def clone_repository(self, repository, destination,
                         source=False, locale=False):
        """Creates copy of repository.

        :return: The the repositories copy, in same order
                 as original.
        """
        # TODO (download gpk)
        # TODO (sources and locales)

        clone = copy.copy(repository)
        clone.url = destination
        path = _get_meta_path(clone, "")
        self.logger.info("clone repository %s to %s", repository, path)
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        release = deb822.Release()
        release["Origin"] = repository.origin
        release["Label"] = repository.origin
        release["Archive"] = repository.name[0]
        release["Component"] = repository.name[1]
        release["Architecture"] = repository.architecture

        with closing(open(os.path.join(path, "Release"), "wb")) as fd:
            release.dump(fd)
        # creates default files
        open(os.path.join(path, "Packages"), "ab").close()
        gzip.open(os.path.join(path, "Packages.gz"), "ab").close()
        return clone

    def _update_main_index(self, repository):
        path = os.path.join(repository.url, "dists", repository.name[0])
        release_path = os.path.join(path, "Release")
        self.logger.info("updated suite release file: %s", release_path)
        with closing(open(release_path, "a+b")) as fd:
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
            try:
                fd.seek(0)
                meta = deb822.Release(fd)
                if len(meta) == 0:
                    self.logger.debug("create suite index %s.", release_path)
                    meta["Origin"] = repository.origin
                    meta["Label"] = repository.origin
                    meta["Suite"] = repository.name[0]
                    meta["Codename"] = repository.name[0].split("-")[0]
                    meta["Architectures"] = repository.architecture
                    meta["Components"] = repository.name[1]
                    meta["Description"] = "The packages repository."
                    for x in _CHECKSUM_METHODS:
                        meta[x] = list()
                    for fpath, size, cs in _get_files_info(repository):
                        fname = fpath[len(path) + 1:]
                        for m, checksum in cs:
                            meta.setdefault(m, []).append({
                                m.lower(): checksum,
                                "size": size,
                                "name": fname
                            })
                else:
                    self.logger.debug("update suite index %s, %s.", release_path)
                    _add_to_string_list(
                        meta, "Architectures", repository.architecture
                    )
                    _add_to_string_list(
                        meta, "Components", repository.name[1]
                    )
                    for fpath, size, cs in _get_files_info(repository):
                        fname = fpath[len(path) + 1:]
                        for m, checksum in cs:
                            for v in meta.setdefault(m, []):
                                if v["name"] == fname:
                                    v["size"] = size
                                    v[m.lower()] = checksum
                                    break
                            else:
                                meta[m].append({
                                    m.lower(): checksum,
                                    "size": size,
                                    "name": fpath[len(path) + 1:]
                                })

                meta["Date"] = datetime.datetime.now().strftime(
                    "%a, %d %b %Y %H:%M:%S %Z"
                )
                fd.truncate(0)
                meta.dump(fd)
            finally:
                fcntl.flock(fd.fileno(), fcntl.LOCK_UN)


def _get_meta_url(repository, filename):
    """Get the meta file url."""
    return "/".join((
        repository.url, "dists", repository.name[0], repository.name[1],
        "binary-" + _ARCHITECTURE_MAPPING[repository.architecture],
        filename
    ))


def _get_meta_path(repository, filename):
    """Get the meta file url."""
    return os.path.join(
        repository.url, "dists", repository.name[0], repository.name[1],
        "binary-" + _ARCHITECTURE_MAPPING[repository.architecture],
        filename
    )


def _is_mandatory(dpkg):
    """Checks that package is mandatory."""
    return _PRIORITIES.get(
        dpkg.get("priority"), _MANDATORY_PRIORITY + 1
    ) < _MANDATORY_PRIORITY


def _get_relations(dpkg, *names):
    """Gets the package relations."""
    relations = list()
    for name in names:
        for variants in dpkg.relations[name]:
            alternative = None
            for v in reversed(variants):
                alternative = PackageRelation(
                    v['name'],
                    _get_version_range(v.get('version')),
                    alternative
                )
            if alternative is not None:
                relations.append(alternative)
    return relations


def _get_version_range(rel_version):
    """Gets the version range."""
    if rel_version is None:
        return VersionRange()
    return VersionRange(
        _OPERATORS_MAPPING[rel_version[0]],
        rel_version[1],
    )


def _get_files_info(repository):
    """Gets the files meta-information."""
    for fname in _REPOSITORY_FILES:
        filepath = _get_meta_path(repository, fname)
        with closing(open(filepath, "rb")) as stream:
            size = os.fstat(stream.fileno()).st_size
            checksum = six.moves.zip(
                _CHECKSUM_METHODS,
                _checksum_collector(stream)
            )
        yield filepath, six.text_type(size), checksum


def _add_to_string_list(target, key, value):
    """Adds new value to the space separated strings."""
    if key in target:
        values = target[key].split()
        if value not in values:
            values.append(value)
            values.sort()
            target[key] = " ".join(values)
    else:
        target[key] = value


def _composite_writer(*files):
    """Makes writer to write into several files simultaneously."""
    def write(s):
        if isinstance(s, six.text_type):
            s = s.encode("utf-8")
        for f in files:
            f.write(s)
    return write