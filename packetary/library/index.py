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


from bintrees import FastRBTree
from collections import defaultdict
import functools
import operator
import six


def _make_operator(direction, op):
    return functools.partial(direction, condition=op)


def _top_down(tree, version, condition):
    """Finds first package from top to down that satisfies condition."""
    result = None
    for item in tree.item_slice(None, version, reverse=True):
        if not condition(item[0], version):
            break
        result = item

    if result is not None:
        return result[1]


def _down_up(self, version, condition):
    """Finds first package from down to up that satisfies condition."""
    result = None
    for item in self.item_slice(version, None):
        if not condition(item[0], version):
            break
        result = item

    if result is not None:
        return result[1]


def _equal(tree, version):
    """Gets the package with specified version."""
    if version in tree:
        return tree[version]


def _newest(tree, _):
    """Gets the package with max version."""
    return tree.max_item()[1]


def _none(*_):
    return None


class Index(object):
    """File location."""
    operators = {
        None: _newest,
        "lt": _make_operator(_top_down, operator.lt),
        "le": _make_operator(_top_down, operator.le),
        "gt": _make_operator(_down_up, operator.gt),
        "ge": _make_operator(_down_up, operator.ge),
        "eq": _equal,
    }

    def __init__(self):
        self.packages = defaultdict(FastRBTree)
        self.obsoletes = defaultdict(FastRBTree)
        self.provides = defaultdict(FastRBTree)

    def __iter__(self):
        return self.get_packages()

    def __len__(self, _reduce=six.functools.reduce):
        return _reduce(
            lambda x, y: x + len(y),
            six.itervalues(self.packages),
            0
        )

    def get_packages(self):
        """Gets the sorted list of packages."""

        for versions in six.itervalues(self.packages):
            for version in versions.values():
                yield version

    def find(self, name, version):
        """Finds the package by name and version.

        :param name: the package`s name.
        :param version: the package`s version.
        :return: the package if it is found, otherwise None
        """

        if name in self.packages:
            p = self._find_version(
                self.packages[name], version
            )
            if p is not None:
                return p

        if name in self.obsoletes:
            return self._resolve_relation(
                self.obsoletes[name], version
            )

        if name in self.provides:
            return self._resolve_relation(
                self.provides[name], version
            )

    def add(self, package):
        """Adds new package to index."""
        self.packages[package.name][package.version] = package
        key = package.name, package.version

        for obsolete in package.obsoletes:
            self.obsoletes[obsolete.name][key] = obsolete

        for provide in package.provides:
            self.provides[provide.name][key] = provide

    def get_unresolved(self, unresolved=None):
        """Gets the unresolved packages.

        :param unresolved: the unresolved depends.
            Note: It will be updated if it is not None.
        :return: the set of unresolved depends.
        """

        if unresolved is None:
            unresolved = set()

        for pkg in self.get_packages():
            requires = six.moves.filterfalse(
                unresolved.__contains__, pkg.requires
            )
            for require in requires:
                rel = require
                while rel is not None:
                    candidate = self.find(rel.name, rel.version)
                    if candidate not in (None, pkg):
                        break
                    rel = rel.option
                if rel is None:
                    unresolved.add(require)
        return unresolved

    def resolve(self, requires, master=None):
        """Resolves requirements.

        :param requires: the set of requirements.
            Note. This parameter will be updated.
        :param master: packages from master is skipped
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
            required = six.moves.filterfalse(unresolved.__contains__, required)
            for require in required:
                rel = require
                while rel is not None:
                    if pkg_filter(rel.name, rel.version) is not None:
                        break
                    candidate = self.find(rel.name, rel.version)
                    if candidate not in (None, pkg):
                        if candidate not in resolved:
                            stack.append((candidate, candidate.requires))
                        break
                    rel = rel.option

                if rel is None:
                    unresolved.add(require)

        resolved.remove(None)
        requires.update(unresolved)
        return resolved

    def _resolve_relation(self, relations, version):
        """Resolve relation according to relations map."""
        for key, candidate in relations.iter_items(reverse=True):
            if candidate.version.has_intersection(version):
                return self.packages[key[0]][key[1]]
        return None

    @staticmethod
    def _find_version(versions, version):
        """Finds concrete version by relation."""
        try:
            op = Index.operators[version.op]
        except KeyError:
            raise ValueError(
                "Undefined operation for versions relation: {0}"
                .format(version.op)
            )
        return op(versions, version.value)
