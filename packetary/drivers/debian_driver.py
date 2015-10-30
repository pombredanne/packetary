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

import abc
import errno
import logging
import os

import six
import six.moves.urllib.parse.urljoin as urljoin
from debian_driver import de

from packetary.drivers.base import RepositoryDriver
from packetary.objects import Package
from packetary.objects import PackageRelation
from packetary.objects import Repository
from packetary.objects import VersionRange


class DebianRepositoryDriver(RepositoryDriver):
    def load_repositories(self, urls, consumer):
        """Gets the repositories from URL.
        :return: the sequence of repositories
        """
        name=(release["Archive"], release["Component"]),
        architecture=release["Architecture"],
        origin=release["origin"],
        url=url

        for url in urls:
        repos =

            for url in urls:
                try:
                  baseurl, section, component =

                release


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

    def _load_repository(self, baseurl, suite, component, consumer):
        """Loads one repository information."""
        release = "/".join((
            baseurl, "dists", suite, component, self.architecture, "Release"
        ))
        stream = connection.open_stream(release)
        deb_release = deb822.Release(connection.open_stream(release))
        consumer(Repository(
            name=(release["Archive"], release["Component"]),
            architecture=release["Architecture"],
            origin=release["origin"],
            url=baseurl
        )

    def load_packages(self, repositories, consumer):
        """Loads packages from repository.
        :param repositories: the repository object
        :param consumer: the package consumer
        """

    @abc.abstractmethod
    def append_packages(self, repository, packages):
        """Assigns new packages to repository.
        :param repository: the target repository
        :param packages: the set of packages
        """

    @abc.abstractmethod
    def clone_repositories(self, repositories, destination):
        """Creates copy of repository.

        :return: The the repositories copy, in same order
                 as original.
        """

    def _copy_package(self, target, package, counter):
        """Synchronises remote file to local fs."""
        offset = 0
        dst_path = os.path.join(target.url, package.filename)
        src_path = urljoin(package.repository.url, package.filename)
        try:
            stats = os.stat(dst_path)
            if stats.st_size == package.size:
                self.logger.debug("file %s skipped.", dst_path)
                return

            if stats.st_size < package.size:
                offset = stats.st_size
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

        self.logger.info(
            "download: %s - %s, offset: %d",
            src_path, dst_path, offset
        )
        self.connection.retrieve(src_path, dst_path, offset)
        counter()
