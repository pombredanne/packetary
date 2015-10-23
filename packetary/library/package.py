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
import collections
import operator
import six


@six.add_metaclass(abc.ABCMeta)
class Package(object):
    """Structure to describe package object."""

    @property
    @abc.abstractmethod
    def name(self):
        """The package`s name."""

    @property
    @abc.abstractmethod
    def version(self):
        """The package`s version."""

    @property
    @abc.abstractmethod
    def size(self):
        """The package`s size in bytes."""

    @property
    @abc.abstractmethod
    def filename(self):
        """The package`s relative path."""

    @property
    @abc.abstractmethod
    def baseurl(self):
        """The repository`s url."""

    @property
    @abc.abstractmethod
    def checksum(self):
        """The package`s checksum.

        :return: tuple(algorithm, checksum).
        """

    @property
    @abc.abstractmethod
    def requires(self):
        """The list of packages(name, version), that requires by packages."""

    @property
    @abc.abstractmethod
    def provides(self):
        """The list of relations, that provides by package."""

    @property
    @abc.abstractmethod
    def obsoletes(self):
        """The list of packages(name, version), that replaces by package."""

    def __hash__(self):
        return hash((self.name, self.version))

    def __cmp__(self, other):
        if self.name < other.name:
            return -1
        if self.name > other.name:
            return 1
        if self.version < other.version:
            return -1
        if self.version > other.version:
            return 1
        return 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __eq__(self, other):
        return self.__cmp__(other) == 0


_RelationBase = collections.namedtuple(
    "Relation", ("name", "version", "option")
)


_VersionRangeBase = collections.namedtuple(
    "_VersionRangeBase", ("op", "value")
)


class VersionRange(_VersionRangeBase):
    """Describes version in package`s relation."""

    def __new__(cls, op=None, value=None):
        if isinstance(op, (list, tuple)):
            if len(op) > 1:
                value = op[1]
            op = op[0]

        return _VersionRangeBase.__new__(cls, op, value)

    def __str__(self):
        if self.value is not None:
            return "%s %s" % (self.op, self.value)
        return "any"

    def has_intersection(self, other):
        if not isinstance(other, VersionRange):
            raise TypeError(
                "Unordered type <type 'VersionRelation'> and %s" % type(other)
            )

        if self.op is None or other.op is None:
            return True

        my_op = getattr(operator, self.op)
        other_op = getattr(operator, other.op)
        if self.op[0] == other.op[0]:
            if self.op[0] == 'l':
                if self.value < other.value:
                    return my_op(self.value, other.value)
                return other_op(other.value, self.value)
            elif self.op[0] == 'g':
                if self.value > other.value:
                    return my_op(self.value, other.value)
                return other_op(other.value, self.value)

        if self.op == 'eq':
            return other_op(self.value, other.value)

        if other.op == 'eq':
            return my_op(other.value, self.value)

        return (
            my_op(other.value, self.value) and
            other_op(self.value, other.value)
        )


class Relation(_RelationBase):
    """Describes the package`s relation."""

    def __new__(cls, name, version=None, option=None):
        if isinstance(name, (list, tuple)):
            if len(name) > 1:
                version = VersionRange(name[1:3])
            if len(name) > 3:
                option = Relation(name[3:])
            name = name[0]
        if version is None:
            version = VersionRange()
        return _RelationBase.__new__(cls, name, version, option)

    def __str__(self):
        if self.option:
            return "%s (%s) | %s" % (self.name, self.version, self.option)
        return "%s (%s)" % (self.name, self.version)
