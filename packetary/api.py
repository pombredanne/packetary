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

import six
import warnings

from packetary.library.context import Context
from packetary.library.index import Index
from packetary.library.package import Relation
from packetary.library.repository import Repository


def create_context(**kwargs):
    """Creates context."""

    return Context(**kwargs)


def _get_set_of_packages(repository,
                         origin,
                         debs=None,
                         bootstrap=None):
    """Get the list of packages related to depends.
    :param repository: the repository manager
    :param origin: the url(s) to origin repository
    :param debs: the url(s) of repositories to get dependency
    :param bootstrap: the additional packages required for bootstrap
    :return: the set of packages
    """
    origin_packages = Index()
    repository.load_packages(origin, origin_packages.add)
    unresolved = set()
    if bootstrap is not None:
        unresolved.update(Relation(r.split()) for r in bootstrap)

    if debs is not None:
        master = Index()
        repository.load_packages(debs, master.add)
    else:
        master = None

    if len(unresolved) > 0 or master is not None:
        packages = origin_packages.resolve(unresolved, master)
    else:
        packages = origin_packages

    if len(unresolved) > 0:
        warnings.warn(
            "The following depends is unresolved: {0}"
            .format(",".join((six.text_type(x) for x in unresolved)))
        )
    return packages


def createmirror(context,
                 kind,
                 arch,
                 destination,
                 origin,
                 debs=None,
                 bootstrap=None,
                 keep_existing=True):
    """Creates mirror of repository(es).

    :param context: the context
    :param kind: the kind of repository
    :param arch: the target architecture
    :param destination: the destination folder
    :param origin: the url(s) to origin repository
    :param debs: the url(s) of repositories to get dependency
    :param bootstrap: the additional packages required for bootstrap
    :param keep_existing: Remove local packages that does not exist in repo.
    :return: the number of copied packages
    """

    repository = Repository(context, kind, arch)
    packages = _get_set_of_packages(
        repository, origin, debs, bootstrap
    )
    repository.copy_packages(packages, destination, keep_existing)
    return len(packages)


def get_packages(context,
                 kind,
                 arch,
                 origin,
                 debs=None,
                 bootstrap=None,
                 formatter=None):
    """Gets list of packages in repository(es).

    :param context: the context
    :param kind: the kind of repository
    :param arch: the target architecture
    :param origin: the url(s) to origin repository
    :param debs: the url(s) of repositories to get dependency
    :param bootstrap: the additional packages required for bootstrap
    :param formatter: the output formatter
    :return: the sequence of packages
    """

    repository = Repository(context, kind, arch)
    packages = _get_set_of_packages(
        repository, origin, debs, bootstrap
    )
    if formatter is not None:
        packages = six.moves.map(formatter, packages)
    return packages


def get_unresolved_depends(context, kind, arch, url, formatter=None):
    """Gets list of unresolved depends for repository(es).

    :param context: the context
    :param kind: the kind of repository
    :param arch: the target architecture
    :param url: the url(s) of repository
    :param formatter: the output formatter
    :return: list of unresolved relations
    """

    repository = Repository(context, kind, arch)
    packages = Index()
    repository.load_packages(url, packages.add)
    unresolved = packages.get_unresolved()
    if formatter is not None:
        unresolved = (formatter(x) for x in unresolved)
    return unresolved
