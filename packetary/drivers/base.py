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
import logging
import os

import six
from six.moves.urllib.parse import urljoin

from packetary.objects.statistics import CopyStatistics


@six.add_metaclass(abc.ABCMeta)
class RepositoryDriver(object):
    """The super class for Repository Drivers.

    To implement support for new type of repository.
    - inherit from this class
    - implement all abstract methods
    - register you driver class in packetary.drivers namespace via endpoints.
    """
    def __init__(self, context):
        self.context = context
        self.logger = logging.getLogger(__package__)

    @abc.abstractmethod
    def parse_urls(self, urls):
        """Parses the repository url.

        :return: the sequence of parsed urls
        """

    @abc.abstractmethod
    def get_repository(self, url, arch, consumer):
        """Loads the repository meta information from URL."""

    @abc.abstractmethod
    def get_packages(self, repository, consumer):
        """Loads packages from repository.

        :param repository: the repository object
        :param consumer: the package consumer
        """

    @abc.abstractmethod
    def clone_repository(self, repository, destination,
                         source=False, locale=False):
        """Creates copy of repository.

        :param source: copy source files
        :param locale: copy localisation
        :return: The copy of repository
        """

    @abc.abstractmethod
    def rebuild_repository(self, repository, packages):
        """Re-builds the repository.

        :param repository: the target repository
        :param packages: the set of packages
        """

    def assign_packages(self, repository, packages, keep_existing=True):
        """Assigns set of packages to the repository.

        :param repository: the target repository
        :param packages: the set of packages
        :param keep_existing:
        """

        if not isinstance(packages, set):
            packages = set(packages)

        if keep_existing:
            consume_exist = packages.add
        else:
            def consume_exist(p):
                if p not in packages:
                    filepath = os.path.join(repository.url, p.filename)
                    self.logger.info("remove package - %s.", filepath)
                    os.remove(filepath)

        self.get_packages(repository, consume_exist)
        self.rebuild_repository(repository, packages)

    def copy_packages(self, repository, packages, keep_existing=True):
        """Copies packages to repository.

        :param repository: the target repository
        :param packages: the set of packages
        :return: statistics
        """
        stat = CopyStatistics()
        with self.context.async_section() as section:
            for package in packages:
                section.execute(
                    self._copy_package, repository, package, stat
                )
        self.assign_packages(repository, packages, keep_existing)
        return stat

    def load_repositories(self, urls, arch, consumer):
        """Loads the repository objects from url.

        :param urls: the list of repository urls.
        :param arch: the target architecture
        :param consumer: the callback to consume objects
        """
        for parsed_url in self.parse_urls(urls):
            self.get_repository(parsed_url, arch, consumer)

    def load_packages(self, repositories, consumer):
        """Loads packages from repository.

        :param repositories: the repository object
        :param consumer: the callback to consume objects
        """
        for r in repositories:
            self.get_packages(r, consumer)

    def clone_repositories(self, repositories, destination,
                           source=False, locale=False):
        """Creates copy of repositories.

        :param source: If True, the source packages will be copied too.
        :param locale: If True, the localisation will be copied too.
        :return: The the copy of repositories in same order.
        """
        result = []
        with self.context.async_section(0) as section:
            for r in repositories:
                result.append(section.execute(
                    self.clone_repository, r, destination,
                    source=source, locale=locale
                ))
        return [x.wait() for x in result]

    @property
    def connection(self):
        """Shortcut for context.connection."""
        return self.context.connection

    def _copy_package(self, target, package, stat):
        """Synchronises remote file to local fs."""
        dst_path = os.path.join(target.url, package.filename)
        src_path = urljoin(package.repository.url, package.filename)
        bytes_copied = self.context.connection.retrieve(
            src_path, dst_path, size=package.filesize
        )
        if package.filesize < 0:
            package.filesize = bytes_copied
        stat.on_package_copied(bytes_copied)
