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


@six.add_metaclass(abc.ABCMeta)
class RepositoryDriver(object):
    def __init__(self, context):
        self.context = context
        self.logger = logging.getLogger(__package__)

    @property
    def connection(self):
        """Shortcut for context.connection."""
        return self.context.connection

    def async_section(self, ignore_errors_count=None):
        """Shortcut for context.async_section."""
        return self.context.async_section(ignore_errors_count)

    def copy_packages(self, repository, packages, stat):
        """Copies packages to repository.
        :param repository: the target repository
        :param packages: the list of packages
        :param stat: statistics
        """
        with self.async_section() as section:
            for package in packages:
                section.execute(
                    self._copy_package, repository, package, stat
                )

        return self.save_packages(repository, packages)

    def load_repositories(self, urls, arch, consumer):
        """Loads the repositories."""
        for parsed_url in self.parse_urls(urls):
            self.get_repository(parsed_url, arch, consumer)

    def load_packages(self, repositories, consumer):
        """Loads packages from repository.
        :param repositories: the repository object
        :param consumer: the package consumer
        """
        for r in repositories:
            self.get_packages(r, consumer)

    def clone_repositories(self, repositories, destination,
                           source=False, locale=False):
        """Creates copy of repositories.

        :param source: copy source files
        :param locale: copy localisation
        :return: The the repositories copy, in same order
                 as original.
        """
        result = []
        with self.async_section(0) as section:
            for r in repositories:
                result.append(section.execute(
                    self.clone_repository, r, destination,
                    source=source, locale=locale
                ))
        return [x.wait() for x in result]

    @abc.abstractmethod
    def parse_urls(self, urls):
        """Parses the repository url.
        :return: the sequence of parsed urls
        """

    @abc.abstractmethod
    def get_repository(self, url, arch, consumer):
        """Loads the repository meta information from URL."""

    @abc.abstractmethod
    def get_packages(self, repositoriy, consumer):
        """Loads packages from repository.
        :param repositoriy: the repository object
        :param consumer: the package consumer
        """

    @abc.abstractmethod
    def save_packages(self, repository, packages):
        """Assigns new packages to repository.
        :param repository: the target repository
        :param packages: the set of packages
        """

    @abc.abstractmethod
    def clone_repository(self, repository, destination,
                         source=False, locale=False):
        """Creates copy of repository.
        :param source: copy source files
        :param locale: copy localisation
        :return: The copy of repository
        """

    def _copy_package(self, target, package, stat):
        """Synchronises remote file to local fs."""
        dst_path = os.path.join(target.url, package.filename)
        src_path = urljoin(package.repository.url, package.filename)
        bytes_copied = self.connection.retrieve(
            src_path, dst_path, size=package.filesize
        )
        if bytes_copied > 0:
            if package.filesize < 0:
                package.filesize = bytes_copied
            stat[0] += 1
        stat[1] += 1
