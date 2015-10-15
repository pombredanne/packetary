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

from packetary.library import repository


logger = logging.getLogger(__package__)


class RepositoryWithIndex(repository.Repository):
    def __init__(self, context, arch):
        self.arch = arch
        self.context = context

    @abc.abstractmethod
    def create_index_writer(self, destination):
        """Creates the index"""

    @abc.abstractmethod
    def load_packages(self, url, consumer):
        """Load packages by url."""

    def parse_urls(self, urls):
        """Iterates over urls.
        Subclasses can ovveride this method.
        """
        return iter(urls)

    def load(self, urls, consumer):
        """See Repository.load"""
        if not isinstance(urls, (list, tuple)):
            urls = [urls]

        with self.context.get_execution_scope() as scope:
            for url in self.parse_urls(urls):
                scope.execute(
                    self.load_packages,
                    url, consumer
                )

    def rebuild_index(self, provider, destination):
        """See the Repository.rebuild_index."""
        index_writer = self.create_index_writer(destination)
        for package in provider:
            index_writer.write(package)
        index_writer.flush()

    def clone(self, provider, destination):
        index_writer = self.create_index_writer(destination)

        with self.context.get_execution_scope() as scope:
            for package in provider:
                scope.execute(self._replicate_package, package, destination)
                index_writer.write(package)
        index_writer.flush()

    def _replicate_package(self, package, destination):
        """Synchronises remote file to local fs."""
        connections = self.context.connections
        offset = 0
        dst_path = os.path.join(destination, package.filename)
        try:
            stats = os.stat(dst_path)
            if stats.st_size == package.size:
                logger.info("file %s is same.", dst_path)
                return

            if stats.st_size < package.size:
                offset = stats.st_size
        except OSError as e:
            if e.errno != 2:
                raise

        logger.info(
            "download: %s - %s, offset: %d",
            package.url, dst_path, offset
        )
        with connections.acquire() as connection:
            connection.retrieve(package.url, dst_path, offset)
