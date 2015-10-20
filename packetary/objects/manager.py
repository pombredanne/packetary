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
import stevedore

from packetary.objects import Index



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

    def clone(self, origin, destination, debs=None,
              bootstrap=None, keep_existing=True):
        """Creates mirror of repository(es).
        :param destination: the destination folder
        :param origin: the url(s) to origin repository
        :param debs: the url(s) of repositories to get dependency
        :param bootstrap: the additional packages required for bootstrap
        :param keep_existing: Remove local packages that does not exist in repo.
        :return: the number of copied packages
        """
        origin_repos = set()
        debs_repos = set()
        self._load_repositories(origin, origin_repos)
        if debs:
            self._load_repositories(debs, debs_repos)

        origin_packages = Index()
        debs_packages = Index()

        repository = Repository(context, kind, arch)
    packages = _get_set_of_packages(
        repository, origin, debs, bootstrap
    )
    repository.copy_packages(packages, destination, keep_existing)
    return len(packages)


    def _load_repositories(self, urls, repositories):
        """Gets the sequence of repositories from URLs."""
        if isinstance(urls, six.text_type):
            urls = [urls]

        for url in urls:
            for repo in self.driver.get_repositories(url):
                repositories.add(repo)


    def _load_packages(self, repositories, packages):
        """Gets the packages from repositories.
        :param repositories: the set of repositories
        :return: the set of packages
        """
        for r in repositories:
            self.driver.load_packages(r, packages.add)






        # repository.load_packages(origin, origin_packages.add)
        # unresolved = set()
        # if bootstrap is not None:
        #     unresolved.update(Relation(r.split()) for r in bootstrap)
        #
        # if debs is not None:
        #     master = Index()
        #     repository.load_packages(debs, master.add)
        # else:
        #     master = None
        #
        # if len(unresolved) > 0 or master is not None:
        #     packages = origin_packages.resolve(unresolved, master)
        # else:
        #     packages = origin_packages
        #
        # if len(unresolved) > 0:
        #     warnings.warn(
        #         "The following depends is unresolved: {0}"
        #         .format(",".join((six.text_type(x) for x in unresolved)))
        #     )
        # return packages



    def get_unresolved(self, unresolved=None):
        """Gets the unresolved packages.

        :param unresolved: the unresolved depends.
            Note: It will be updated if it is not None.
        :return: the set of unresolved depends.
        """

        if unresolved is None:
            unresolved = set()

        for pkg in self.get_packages():
            for require in pkg.requires:
                rel = require
                while rel is not None:
                    if rel not in unresolved:
                        candidate = self.find(rel.name, rel.version)
                        if candidate is not None and candidate != pkg:
                            break

                    rel = rel.alternative
                if rel is None:
                    unresolved.add(require)
        return unresolved

    def resolve(self, requires, master=None):
        """Resolves requirements.

        :param requires: the set of requirements.
                         Note. This set will be updated.
        :param master: the master index,
                       all packages from master index will be skipped.
        :return: The set of resolved depends.
        """

        unresolved = set()
        resolved = set()
        if master is None:
            pkg_filter = _none
        else:
            pkg_filter = master.find
            requires.update(master.get_unresolved())

        stack = list()
        stack.append((None, requires.copy()))
        requires.clear()

        while len(stack) > 0:
            pkg, required = stack.pop()
            resolved.add(pkg)
            for require in required:
                rel = require
                while rel is not None:
                    if rel not in unresolved:
                        if pkg_filter(rel.name, rel.version) is not None:
                            break
                        candidate = self.find(rel.name, rel.version)
                        if candidate is not None and candidate != pkg:
                            if candidate not in resolved:
                                stack.append((candidate, candidate.requires))
                            break
                    rel = rel.alternative

                if rel is None:
                    unresolved.add(require)

        resolved.remove(None)
        requires.update(unresolved)
        return resolved