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

from packetary.objects import Index
from packetary.objects import PackageRelation


logger = logging.getLogger(__package__)


class RepositoryManager(object):
    """Repository Manager."""

    _drivers = None

    def __init__(self, driver):
        self.driver = driver

    @classmethod
    def create(cls, context, name, architecture):
        """Creates the repository manager."""
        if cls._drivers is None:
            cls._drivers = stevedore.ExtensionManager("packetary.drivers")
        return cls._drivers[name](context, architecture)

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
        """Creates mirror of repository(es).
        :param destination: the destination folder
        :param origin: the url(s) to origin repository
        :param debs: the url(s) of repositories to get dependency
        :param bootstrap: the additional list of relations
        :param keep_existing: Remove local packages that does not exist in repo.
        :return: the number of copied packages
        """

        repos, packages = self._load_repositories_with_packages(
            origin, debs, bootstrap
        )

        repos2packages = dict((x, set()) for x in repos)

        mirrors = dict()
        for repo in repos:
            logger.info("clone repository: %s", repo.name)
            mirror = self.driver.clone(repo, destination)
            packages = repos2packages[repo]
            if keep_existing:
                logger.info("load existing from repository: %s", repo.name)
                self.driver.load_packages(mirror, packages.add)
            else:
                def remove_package(p):
                    if p not in packages:
                        filepath = os.path.join(repo.url, packages.filename)
                        logger.info("remove package - %s.", filepath)
                        os.remove(repo.url + packages.filename)

                logger.info("remove extra packages from repository: %s", repo.name)
                self.driver.load_packages(repo, remove_package)
            mirrors[repo] = mirror

        for repo, packages in six.iteritems(repos2packages):
            logger.info("update repository: %s", repo.name)
            self.driver.append_packages(mirrors[repo], packages)

    def get_unresolved_dependens(self, url):
        """Gets list of unresolved depends for repository(es).
        :param url: the url(s) of repository
        :return: list of unresolved relations
        """
        packages = Index()
        self._load_packages(
            self._load_repositories(url),
            packages
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
        origin_packages = Index()
        debs_packages = None

        origin_repos = self._load_repositories(origin)
        self._load_packages(origin_repos, origin_packages)
        if debs is not None:
            debs_packages = Index()
            self._load_packages(
                self._load_repositories(origin),
                debs_packages
            )

        unresolved = set()
        if bootstrap is not None:
            unresolved.update(PackageRelation(r.split()) for r in bootstrap)

        return (
            origin_repos,
            self._get_minimal_subset(origin_packages, debs_packages, bootstrap)
        )

    def _load_repositories(self, urls):
        """Gets the sequence of repositories from URLs."""
        if isinstance(urls, six.text_type):
            urls = [urls]

        repos = set()
        for url in urls:
            for repo in self.driver.get_repositories(url):
                repos.add(repo)
        return repos

    def _load_packages(self, repositories, index):
        """Gets the packages from repositories.
        :param repositories: the set of repositories
        :return: the set of packages
        """
        for r in repositories:
            self.driver.load_packages(r, index.add)

    def _get_minimal_subset(self, packages, master, requires):
        """Gets the sub-set of required packages.
        :param packages: the set of packages
        :param master: the master index,
                       all packages from master index will be skipped.
        :param requires: the set of requirements.
                         Note. This set will be updated.
        :return: The set of resolved depends.
        """

        unresolved = set()
        resolved = set()
        if master is None:
            def pkg_filter(*_):
                pass
        else:
            pkg_filter = master.find
            self._get_unresolved_depends(master, requires)

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
        requires.update(unresolved)
        return resolved

    @staticmethod
    def _get_unresolved_depends(packages, unresolved):
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
