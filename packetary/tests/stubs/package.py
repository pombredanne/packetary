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

from packetary.library import package
import functools

VersionRange = package.VersionRange

Relation = package.Relation

class Package(package.Package):
    def __init__(self, **kwargs):
        self.props = kwargs
        self.props.setdefault('name', 'test')
        self.props.setdefault('version', 1)
        self.props.setdefault('arch', 'x86_64')
        self.props.setdefault('size', 0)
        self.props.setdefault('checksum', (None, None))
        self.props.setdefault('url', "test.pkg")
        self.props.setdefault('requires', [])
        self.props.setdefault('provides', [])
        self.props.setdefault('obsoletes', [])

    def _get_property(self, name=None):
        return self.props[name]

    name = lambda self: self._get_property("name")
    version = lambda self: self._get_property("version")
    arch = lambda self: self._get_property("arch")
    size = lambda self: self._get_property("size")
    checksum = lambda self: self._get_property("checksum")
    url = lambda self: self._get_property("url")
    requires = lambda self: self._get_property("requires")
    provides = lambda self: self._get_property("provides")
    obsoletes = lambda self: self._get_property("obsoletes")
