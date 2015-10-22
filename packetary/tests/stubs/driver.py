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

import mock
import six

from packetary.library import driver
from packetary.tests.stubs import package



def gen_relation(pattern, idx, version=None):
    if pattern is not None:
        return [
            package.Relation(
                pattern.format(idx), package.VersionRange(version)
            )
        ]
    return []


def package_generator(count=1, prefix='package',
                      requires_mask=None,
                      obsoletes_mask=None,
                      provides_mask=None,
                      **kwargs):
    packages = []
    for i in six.moves.range(count):
        requires = gen_relation(requires_mask, i)
        obsoletes = gen_relation(obsoletes_mask, i, ["le", 2])
        provides = gen_relation(provides_mask, i, ["gt", 1])
        packages.append(package.Package(
            name="{0}-{1}".format(prefix, i),
            requires=requires,
            obsoletes=obsoletes,
            provides=provides,
            **kwargs
        ))
    return packages


class RepoDriver(driver.RepoDriver):
    def __init__(self, packages_gen=None):
        self.packages = None
        self.index_writer = mock.MagicMock()
        if packages_gen is None:
            self.packages_gen = package_generator
        else:
            self.packages_gen = packages_gen

    def __call__(self, *_):
        return self

    def parse_urls(self, urls):
        for url in urls:
            yield url, "test"

    def get_path(self, base, p):
        return "/".join((base or p.baseurl, p.filename))

    def create_index(self, destination):
        return self.index_writer

    def load(self, baseurl, reponame, consumer):
        for p in self.packages_gen(baseurl=baseurl):
            consumer(p)
