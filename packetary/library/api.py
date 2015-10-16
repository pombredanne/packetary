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

from .index import Index


def createmirror(driver, destination, origin, debs=None):
    """Creates mirror.
    :param driver: the repository driver
    :param destination: the destination folder
    :param origin: the url(s) to origin repository
    :param debs: the url(s) of repositories to get dependency
    :return: the number of copied packages
    """
    packages = Index()
    driver.load(origin, packages.add)
    if debs is not None:
        requires = Index()
        driver.load(debs, requires.add)
        requires = requires.get_unresolved()
        if len(requires) == 0:
            return 0
        packages = packages.resolve(requires)

    driver.clone(packages, destination)
    return len(packages)


def get_packages(driver, url, formatter=None):
    """Gets list of packages.
    :param driver: the repository driver
    :param url: the url(s) of repository
    :param formatter: the output formatter
    """
    packages = []
    consumer = packages.append
    if formatter is not None:
        consumer = lambda x: consumer(formatter(x))
    driver.load(url, consumer)
    return packages


def get_unresolved_depends(driver, url, formatter=None):
    """Gets list of unresolved depends.
    :param driver: the repository driver
    :param url: the url(s) of repository
    :param formatter: the output formatter
    """
    packages = Index()
    driver.load(url, packages.add)
    unresolved = packages.get_unresolved()
    if formatter is not None:
        unresolved = (formatter(x) for x in unresolved)
    return unresolved
