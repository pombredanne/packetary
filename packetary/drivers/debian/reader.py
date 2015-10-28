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

from __future__ import print_function

import logging

from debian import deb822
from debian import debian_support

from packetary.objects.repository import Repository
from packetary.objects.package_relation import Relation
from packetary.objects.package_relation import VersionRange
from packetary.objects.package import Checksum
from packetary.objects.package import Package
from packetary.library.streams import GzipDecompress


logger = logging.getLogger(__package__)


def load_packages(context, url, consumer):
    """Loads the packages from repository."""

    release = "/".join((url, "Release"))
    index = "/".join((url, "Packages.gz"))
    with context.get_connection() as connection:
        logger.debug("release file - %s", release)
        stream = connection.open_stream(release)
        repo = _release2repository(
            url.rsplit("/", 4)[0], deb822.Release(stream)
        )
        logger.debug("index file - %s", index)
        stream = GzipDecompress(connection.open_stream(index))
        pkg_iter = deb822.Packages.iter_paragraphs(stream)
        counter = 0
        for dpkg in pkg_iter:
            consumer(_dpkg2package(dpkg, repo))
            counter += 1

        logger.info("loaded: %d packages from %s.", counter, index)


def _release2repository(url, release):
    return Repository(
        name=(release["Archive"], release["Component"]),
        architecture=release["Architecture"],
        origin=release["origin"],
        url=url
    )


def _dpkg2package(dpkg, repository):
    p = Package(
        name=dpkg["package"],
        version=debian_support.Version(dpkg['version']),
        size=int(dpkg['size']),
        filename=dpkg["filename"],
        checksum=Checksum(
            md5=dpkg.get("MD5Sum"),
            sha1=dpkg.get("sha1"),
            sha256=dpkg.get("sha256")
        ),
        requires=_get_relations(dpkg, "depends", "pre-depends"),
        obsoletes=_get_relations(dpkg, "replaces"),
        provides=_get_relations(dpkg, "provides"),
        repository=repository
    )
    return p


def _get_relations(dpkg, *names):
    relations = list()
    for name in names:
        for variants in dpkg.relations[name]:
            option = None
            for v in reversed(variants):
                option = Relation(
                    v['name'],
                    _get_version_range(v.get('version')),
                    option
                )
            if option is not None:
                relations.append(option)
    return relations


_OPERATORS_MAPPING = {
    '>>': 'gt',
    '<<': 'lt',
    '=': 'eq',
    '>=': 'ge',
    '<=': 'le',
}


def _get_version_range(rel_version):
    if rel_version is None:
        return VersionRange()
    return VersionRange(
        _OPERATORS_MAPPING[rel_version[0]],
        rel_version[1],
    )


if __name__ == "__main__":
    from packetary.context import Context

    ctx = Context()
    load_packages(ctx, "http://mirror.yandex.ru/ubuntu/dists/trusty/main/binary-amd64", print)
