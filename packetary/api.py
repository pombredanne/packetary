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

import logging

import six

from packetary.controllers import RepositoryController
from packetary.library.connections import ConnectionsManager
from packetary.library.executor import AsynchronousSection
from packetary.objects import Index
from packetary.objects import PackageRelation
from packetary.objects import PackagesTree
from packetary.objects.statistics import CopyStatistics


logger = logging.getLogger(__package__)


class Configuration(object):
    """The configuration holder."""

    def __init__(self, http_proxy=None, https_proxy=None,
                 retries_num=0, threads_num=0,
                 ignore_errors_num=0):
        """Initialises.

        :param http_proxy: the url of proxy for connections over http,
                           no-proxy will be used if it is not specified
        :param https_proxy: the url of proxy for connections over https,
                            no-proxy will be used if it is not specified
        :param retries_num: the number of retries on errors
        :param threads_num: the max number of active threads
        :param ignore_errors_num: the number of errors that may occurs
                before stop processing
        """

        self.http_proxy = http_proxy
        self.https_proxy = https_proxy
        self.ignore_error_count = ignore_errors_num
        self.retries_num = retries_num
        self.thread_count = threads_num


class Context(object):
    """The infra-objects holder."""

    def __init__(self, config):
        """Initialises.

        :param config: the configuration
        """
        self._connection = ConnectionsManager(
            proxy=config.http_proxy,
            secure_proxy=config.https_proxy,
            retries_num=config.retries_count
        )
        self._thread_count = config.thread_count
        self._ignore_error_count = config.ignore_error_count

    @property
    def connection(self):
        """Gets the connection."""
        return self._connection

    def async_section(self, ignore_errors_num=None):
        """Gets the execution scope.

        :param ignore_errors_num: custom value for ignore_errors_num,
                                  the class value is used if omitted.
        """
        if ignore_errors_num is None:
            ignore_errors_num = self._ignore_error_count

        return AsynchronousSection(self._thread_count, ignore_errors_num)


class RepositoryApi(object):
    """Repository Manager."""
    def __init__(self, controller):
        """Initialises.

        :param controller: the repository controller."""
        self.controller = controller

    @classmethod
    def create(cls, config, kind, arch):
        """Creates the repository manager.

        :param config: the configuration
        :param kind: the kind of repository(deb, yum, etc)
        :param arch: the architecture of repository (x86_64 or i386)
        """
        if isinstance(config, Context):
            context = config
        else:
            context = Context(config)

        return cls(RepositoryController.load(context, kind, arch))

    def get_packages(self, origin, debs=None, bootstrap=None):
        """Gets the list of packages from repository(es).

        :param origin: the url(s) to origin repository
        :param debs: the url(s) of repositories to get dependency
        :param bootstrap: the list of additional package names
        :return: set of packages
        """
        repositories = self._get_repositories(origin)
        return self._get_packages(repositories, debs, bootstrap)

    def clone_repositories(self, origin, destination, debs=None,
                           bootstrap=None, keep_existing=True,
                           include_source=False, include_locale=False):
        """Creates clone of repository(es).

        :param destination: the destination folder
        :param origin: the url(s) to origin repository
        :param debs: the url(s) of repositories to get dependency
        :param bootstrap: the list of additional package names
        :param keep_existing: If False - local packages that does not exist
                              in original repo will be removed.
        :param include_source: if True, the source packages will be copied too.
        :param include_locale: if True, the locales will be copied too.
        :return: Statistics of copied and total packages
        """
        repositories = self._get_repositories(origin)
        packages = self._get_packages(repositories, debs, bootstrap)
        mirrors = self.controller.clone_repositories(
            repositories, destination, include_source, include_locale
        )

        package_groups = dict((x, set()) for x in repositories)
        for pkg in packages:
            package_groups[pkg.repository].add(pkg)

        stat = CopyStatistics()
        for repo, packages in six.iteritems(package_groups):
            mirror = mirrors[repo]
            logger.info("copy packages from - %s", repo)
            self.controller.copy_packages(
                mirror, packages, keep_existing, stat.on_package_copied
            )
        return stat

    def get_unresolved_depends(self, urls):
        """Gets list of unresolved depends for repository(es).

        :param urls: the url(s) of repository
        :return: list of unresolved relations
        """
        packages = PackagesTree()
        self.controller.load_packages(
            self._get_repositories(urls),
            packages.add
        )
        return packages.get_unresolved_depends()

    def _get_repositories(self, urls):
        """Gets the set of repositories by url."""
        repositories = set()
        self.controller.load_repositories(urls, repositories.add)
        return repositories

    def _get_packages(self, repositories, master, requirements):
        """Gets the list of packages according to master and requirements."""
        if master is None and requirements is None:
            packages = set()
            self.controller.load_packages(repositories, packages.add)
            return packages

        packages = PackagesTree()
        self.controller.load_packages(repositories, packages.add)
        if master is not None:
            main_index = Index()
            self.controller.load_packages(
                self._get_repositories(master),
                main_index.add
            )
        else:
            main_index = None

        requirements = self._parse_requirements(requirements)
        return packages.get_minimal_subset(main_index, requirements)

    @staticmethod
    def _parse_requirements(requirements):
        """Gets the list of relations from requirements.
        :param requirements: the list of requirement in next format.
                             "name [comparison edge]|[alternative [comparison edge]]
        """
        if requirements is not None:
            return set(
                PackageRelation.from_args(
                    *(x.split() for x in r.split("|"))) for r in requirements
            )
        return set()
