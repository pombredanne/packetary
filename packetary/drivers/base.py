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
import six


@six.add_metaclass(abc.ABCMeta)
class RepositoryDriver(object):
    def __init__(self, context, architecture):
        self.context = context
        self.architecture = architecture

    @abc.abstractmethod
    def get_repositories(self, url):
        """Gets the repositories from URL.
        :return: the sequence of repositories
        """

    @abc.abstractmethod
    def load_packages(self, repository, consumer):
        """Loads packages from repository.
        :param repository: the repository object
        :param consumer: the package consumer
        """

    @abc.abstractmethod
    def append_packages(self, repository, packages):
        """Assigns new packages to repository.
        :param repository: the target repository
        :param packages: the set of packages
        """

    @abc.abstractmethod
    def clone_repository(self, repository, destination):
        """Creates copy of repository.

        :return: The new repository
        """
