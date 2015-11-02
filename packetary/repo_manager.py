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
import os
import warnings

import six
import stevedore

from packetary.library.connections import ConnectionsManager
from packetary.library.executor import AsynchronousSection
from packetary.objects import Index
from packetary.objects import PackageRelation
from packetary.objects.statistics import CopyStatistics


logger = logging.getLogger(__package__)


class UnresolvedWarning(UserWarning):
    """Warning about unresolved depends."""
    pass


class Configuration(object):
    """The configuration object."""

    def __init__(self, http_proxy=None, https_proxy=None,
                 retries_count=0, thread_count=0,
                 ignore_error_count=0):
        """Initialises.

        :param http_proxy: the proxy address for http-connections
        :param https_proxy: the proxy address for https-connections
        :param retries_count: the number of retries on errors
        :param thread_count: the max number of active threads
        :param ignore_error_count: the number of errors that may occurs
                before stop processing
        """

        self.http_proxy = http_proxy
        self.https_proxy = https_proxy
        self.ignore_error_count = ignore_error_count
        self.retries_count = retries_count
        self.thread_count = thread_count


class Context(object):
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
        """Gets the execution scope"""
        if ignore_errors_num is None:
            ignore_errors_num = self._ignore_error_count

        return AsynchronousSection(self._thread_count, ignore_errors_num)


class RepositoryManager(object):
    """Repository Manager."""

    _drivers = None

    def __init__(self, driver, arch):
        """Initialises.

        :param driver: the repo driver instance"""
        self.driver = driver
        self.arch = arch

    @classmethod
    def create(cls, config, kind, arch):
        """Creates the repository manager.

        :param config: the configuration
        :param kind: the kind of repository(deb, yum, etc)
        :param arch: the architecture of repository (x86_64 or i386)
        """
        if cls._drivers is None:
            cls._drivers = stevedore.ExtensionManager("packetary.drivers")
        if isinstance(config, Context):
            context = config
        else:
            context = Context(config)

        return cls(cls._drivers[kind].plugin(context), arch)

    def get_packages(self, origin, debs=None, bootstrap=None):
        """Gets the list of packages from repository(es).

        :param origin: the url(s) to origin repository
        :param debs: the url(s) of repositories to get dependency
        :param bootstrap: the list of additional package names
        :return: set of packages
        """
        _, packages = self._load_repositories_with_packages(
            origin, debs, bootstrap
        )
        return packages

    def clone_repositories(self, origin, destination, debs=None,
                           bootstrap=None, keep_existing=True):
        """Creates clone of repository(es).

        :param destination: the destination folder
        :param origin: the url(s) to origin repository
        :param debs: the url(s) of repositories to get dependency
        :param bootstrap: the list of additional package names
        :param keep_existing: If False - local packages that does not exist
                              in original repo will be removed.
        :return: Statistics copied and total packages
        """
        repos, packages = self._load_repositories_with_packages(
            origin, debs, bootstrap
        )

        # mirror -> origin
        mirros = dict(six.moves.zip(
            repos,
            self.driver.clone_repositories(
                repos, os.path.abspath(destination)
            )
        ))

        package_groups = dict((x, set()) for x in repos)
        for pkg in packages:
            package_groups[pkg.repository].add(pkg)

        stat = CopyStatistics()
        for repo, packages in six.iteritems(package_groups):
            mirror = mirros[repo]
            logger.info("copy packages from - %s", repo)
            self.driver.copy_packages(
                mirror, packages, keep_existing, stat.on_package_copied
            )
        return stat

    def get_unresolved_depends(self, url):
        """Gets list of unresolved depends for repository(es).

        :param url: the url(s) of repository
        :return: list of unresolved relations
        """
        packages = Index()
        self.driver.load_packages(
            self._load_repositories(url),
            packages.add
        )
        return self._get_unresolved_depends(packages)

    def _load_repositories_with_packages(
            self, origin, debs=None, bootstrap=None):
        """Gets the repositories and packages.

        :param origin: the url(s) to origin repository
        :param debs: the url(s) of repositories to get dependency
        :param bootstrap: the list of additional package names
        :return: the number of copied packages
        """
        if debs is not None:
            rdepends = Index()
            self.driver.load_packages(
                self._load_repositories(debs),
                rdepends.add
            )
        else:
            rdepends = None

        unresolved = set()
        if bootstrap is not None:
            unresolved.update(
                PackageRelation.from_args(r.split()) for r in bootstrap
            )

        repos = self._load_repositories(origin)
        if rdepends is not None or len(unresolved) > 0:
            packages = Index()
            self.driver.load_packages(repos, packages.add)
            packages = self._get_minimal_subset(packages, rdepends, unresolved)
        else:
            packages = set()
            self.driver.load_packages(repos, packages.add)

        if len(unresolved) > 0:
            msg = "unresolved depends:\n {0}\n".format(
                ", ".join(six.text_type(x) for x in sorted(unresolved))
            )
            warnings.warn(UnresolvedWarning(msg))
        return repos, packages

    def _load_repositories(self, urls):
        """Gets the sequence of repositories from URLs."""
        if isinstance(urls, six.string_types):
            urls = [urls]
        repos = set()
        self.driver.load_repositories(urls, self.arch, repos.add)
        return repos

    @staticmethod
    def _get_minimal_subset(index, rdepends, requires):
        """Gets the sub-set of required packages.

        :param index: the packages index
        :param rdepends: the index of reversed depends,
                       all packages from master index will be skipped.
        :param requires: the set of requirements.
                         Note. This set will be updated.
        :return: The set of resolved depends.
        """

        unresolved = set()
        resolved = set()
        if rdepends is None:
            def pkg_filter(*_):
                pass
        else:
            pkg_filter = rdepends.find
            RepositoryManager._get_unresolved_depends(rdepends, requires)

        stack = list()
        stack.append((None, requires))

        for pkg in index:
            if pkg.mandatory:
                stack.append((pkg, pkg.requires))

        while len(stack) > 0:
            pkg, required = stack.pop()
            resolved.add(pkg)
            for require in required:
                for rel in require:
                    if rel not in unresolved:
                        if pkg_filter(rel.name, rel.version) is not None:
                            break
                        # use all packages that meets depends
                        candidates = index.find_all(rel.name, rel.version)
                        found = False
                        for cand in candidates:
                            if cand == pkg:
                                continue
                            found = True
                            if cand not in resolved:
                                stack.append((cand, cand.requires))

                        if found:
                            break
                else:
                    unresolved.add(require)

        resolved.remove(None)
        requires.clear()
        requires.update(unresolved)
        return resolved

    @staticmethod
    def _get_unresolved_depends(index, unresolved=None):
        """Gets the set of unresolved depends.

        :param index: the packages index.
            Note: It will be updated if it is not None.
        :return: the set of unresolved depends.
        """

        if unresolved is None:
            unresolved = set()

        for pkg in index:
            for require in pkg.requires:
                for rel in require:
                    if rel not in unresolved:
                        candidate = index.find(rel.name, rel.version)
                        if candidate is not None and candidate != pkg:
                            break
                else:
                    unresolved.add(require)
        return unresolved
