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
import warnings

from packetary import api
from packetary.library.repository import Repository
from packetary.tests import base
from packetary.tests.stubs.context import Context
from packetary.tests.stubs.driver import package_generator
from packetary.tests.stubs.driver import RepoDriver


@mock.patch("packetary.api.Repository")
class TestApi(base.TestCase):
    def setUp(self):
        super(TestApi, self).setUp()
        self.context = Context()
        packages_gen = mock.MagicMock()
        packages_gen.side_effect = [
            package_generator(3, prefix="requires"),
            package_generator(1, requires_mask="requires-{0}"),
        ]
        drivers = mock.MagicMock()
        drivers.test.return_value = RepoDriver(packages_gen)
        self.repo = Repository(
            self.context, "test", "x86_64", drivers=drivers
        )

    def test_createmirror_with_deps(self, repo_class):
        repo_class.return_value = self.repo
        count = api.createmirror(
            self.context,
            "test", "x86_64",
            "target",
            "file:///origin",
            "file:///debs",
            ["requires-1",
             "package-0"],
            True
        )
        repo_class.assert_called_once_with(
            self.context, "test", "x86_64"
        )
        self.assertEqual(2, count)

    def test_createmirror_warns_unresolved(self, repo_class):
        repo_class.return_value = self.repo
        with warnings.catch_warnings(record=True) as warns:
            count = api.createmirror(
                self.context,
                "test", "x86_64",
                "target",
                "file:///origin",
                "file:///debs",
                ["unresolved"],
                True
            )
        self.assertEqual(1, count)
        warns = [six.text_type(x.message) for x in warns]
        self.assertIn(
            "The following depends is unresolved: unresolved (any)",
            warns
        )

    def test_createmirror_full(self, repo_class):
        repo_class.return_value = self.repo
        count = api.createmirror(
            self.context,
            "test", "x86_64",
            "target",
            "file:///origin"
        )
        self.assertEqual(3, count)

    def test_get_packages(self, repo_class):
        repo_class.return_value = self.repo
        packages = api.get_packages(
            self.context, "test", "x86_64", "http://localhost"
        )
        repo_class.assert_called_once_with(
            self.context, "test", "x86_64"
        )
        self.assertEqual(3, len(packages))
        self.assertEqual(
            "requires-0", packages[0].name
        )
        packages = api.get_packages(
            self.context, "test", "x86_64",
            "http://localhost",
            formatter=lambda x: x.name
        )
        self.assertItemsEqual(
            ["package-0"],
            packages
        )

    def test_get_unresolved_depends(self, repo_class):
        repo_class.return_value = self.repo
        unresolved = iter(api.get_unresolved_depends(
            self.context, "test", "x86_64", "http://localhost"
        ))
        repo_class.assert_called_once_with(
            self.context, "test", "x86_64"
        )
        self.assertIsNone(next(unresolved, None))
        unresolved = iter(api.get_unresolved_depends(
            self.context, "test", "x86_64", "http://localhost"
        ))
        self.assertEqual(
            "requires-0 (any)",
            six.text_type(next(unresolved, None))
        )

    def test_get_unresolved_depends_with_format(self, repo_class):
        repo_class.return_value = self.repo
        api.get_unresolved_depends(
            self.context, "test", "x86_64", "http://localhost"
        )
        unresolved = iter(api.get_unresolved_depends(
            self.context, "test", "x86_64", "http://localhost",
            formatter=lambda x: x.package
        ))
        self.assertEqual(
            "requires-0",
            next(unresolved, None)
        )
