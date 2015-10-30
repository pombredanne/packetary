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

import six
import stevedore

from packetary.library.connections import ConnectionsManager
from packetary.library.executor import AsynchronousSection
from packetary.objects import Index
from packetary.objects import PackageRelation


logger = logging.getLogger(__package__)


class Configuration(object):
    """The configuration object."""

    def __init__(self, http_proxy=None, https_proxy=None,
                 retries_count=0, thread_count=None,
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
    DEFAULT_THREAD_COUNT = 1

    def __init__(self, config):
        """Initialises.
        :param config: the configuration
        """
        self._connection = ConnectionsManager(
            proxy=config.http_proxy,
            secure_proxy=config.https_proxy,
            retries_num=config.retries_count
        )
        self._thread_count = config.thread_count or self.DEFAULT_THREAD_COUNT
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
    def create(cls, config, name, arch):
        """Creates the repository manager."""
        if cls._drivers is None:
            cls._drivers = stevedore.ExtensionManager("packetary.drivers")
        if isinstance(config, Context):
            context = config
        else:
            context = Context(config)

        return cls(cls._drivers[name].plugin(context), arch)

    def get_packages(self, origin, debs=None, bootstrap=None):
        """Gets the list of packages from repository(es).
        :param origin: the url(s) to origin repository
        :param debs: the url(s) of repositories to get dependency
        :param bootstrap: the additional list of relations
        :return: set of packages
        """
        _, packages = self._load_repositories_with_packages(
            origin, debs, bootstrap
        )
        return packages

    def clone(self, origin, destination, debs=None,
              bootstrap=None, keep_existing=True):
        """Creates mirror for repository(es).
        :param destination: the destination folder
        :param origin: the url(s) to origin repository
        :param debs: the url(s) of repositories to get dependency
        :param bootstrap: the additional list of relations
        :param keep_existing: Remove local packages that does not exist in repo.
        :return: tuple(actually copied, total packages count)
        """
        repos, packages = self._load_repositories_with_packages(
            origin, debs, bootstrap
        )
        mirros = dict(six.moves.zip(
            repos,
            self.driver.clone_repositories(
                repos, os.path.abspath(destination)
            )
        ))

        package_groups = dict((x, set()) for x in repos)
        for pkg in packages:
            package_groups[pkg.repository].add(pkg)

        if keep_existing:
            def consume_exist(p):
                package_groups[p.repository].add(p)

        else:
            def consume_exist(p):
                if p not in package_groups[p.repository]:
                    filepath = os.path.join(repo.url, packages.filename)
                    logger.info("remove package - %s.", filepath)
                    os.remove(repo.url + packages.filename)

        self.driver.load_packages(
            six.itervalues(mirros),
            consume_exist
        )

        stat = [0, 0]
        for repo, packages in six.iteritems(package_groups):
            logger.info("update repository: %s", repo.name)
            self.driver.copy_packages(mirros[repo], packages, stat)
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
        :param bootstrap: the additional list of relations
        :return: the number of copied packages
        """
        packages = Index()
        repos = self._load_repositories(origin)
        self.driver.load_packages(repos, packages.add)

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
            unresolved.update(PackageRelation(r.split()) for r in bootstrap)

        subset = self._get_minimal_subset(packages, rdepends, unresolved)
        if len(unresolved) > 0:
            six.print_("WARNING: unresolved depends:\n {0}".format(
                ", ".join(six.text_type(x) for x in sorted(unresolved))
            ))
        return repos, subset

    def _load_repositories(self, urls):
        """Gets the sequence of repositories from URLs."""
        if isinstance(urls, six.text_type):
            urls = [urls]
        repos = set()
        self.driver.load_repositories(urls, self.arch, repos.add)
        return repos

    def _get_minimal_subset(self, packages, rdepends, requires):
        """Gets the sub-set of required packages.
        :param packages: the set of packages
        :param rdepends: the master index,
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
            self._get_unresolved_depends(rdepends, requires)

        stack = list()
        stack.append((None, requires))

        for pkg in packages:
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
                        candidate = packages.find(rel.name, rel.version)
                        if candidate is not None and candidate != pkg:
                            if candidate not in resolved:
                                stack.append((candidate, candidate.requires))
                            break
                else:
                    unresolved.add(require)

        resolved.remove(None)
        requires.clear()
        requires.update(unresolved)
        return resolved

    @staticmethod
    def _get_unresolved_depends(packages, unresolved=None):
        """Gets the set of unresolved depends.
        :param packages: the unresolved depends.
            Note: It will be updated if it is not None.
        :return: the set of unresolved depends.
        """

        if unresolved is None:
            unresolved = set()

        for pkg in packages:
            for require in pkg.requires:
                for rel in require:
                    if rel not in unresolved:
                        candidate = packages.find(rel.name, rel.version)
                        if candidate is not None and candidate != pkg:
                            break
                else:
                    unresolved.add(require)
        return unresolved
