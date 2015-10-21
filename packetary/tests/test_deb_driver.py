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

from __future__ import with_statement

import mock
import os

from packetary.library.drivers import deb_driver
from packetary.tests import base
from packetary.tests.stubs.context import Context


PACKAGES_GZ = os.path.join(os.path.dirname(__file__), "data", "packages.gz")


class TestDebDriver(base.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestDebDriver, cls).setUpClass()
        cls.driver = deb_driver.Driver(
            Context(),
            "x86_64"
        )

    def test_get_path(self):
        package = mock.MagicMock()
        package.baseurl = "."
        package.filename = "test.dpkg"
        self.assertEqual(
            "dir/test.dpkg",
            self.driver.get_path("dir", package)
        )
        self.assertEqual(
            "./test.dpkg",
            self.driver.get_path(None, package)
        )

    @mock.patch("packetary.library.drivers.deb_driver")
    def test_load(self, _):
        packages = []
        connection = self.driver.connections.connection
        with open(PACKAGES_GZ, "rb") as stream:
            connection.open_stream.return_value = stream
            self.driver.load(
                "http://host", ("trusty", "main"), packages.append
            )

        connection.open_stream.assert_called_once_with(
            "http://host/dists/trusty/main/binary-amd64/Packages.gz",
        )
        self.assertEqual(1, len(packages))
        self.assertEqual("libjs-angularjs", packages[0].name)
        self.assertEqual("1.3.17-1~u14.04+mos1", packages[0].version)
        self.assertEqual(399294, packages[0].size)
        self.assertEqual(
            ("sha1", "402bd18c145ae3b5344edf07f246be159397fd40"),
            packages[0].checksum
        )
        self.assertEqual(
            "pool/main/a/angular.js/"
            "libjs-angularjs_1.3.17-1~u14.04+mos1_all.deb",
            packages[0].filename
        )

    def test_parse_urls(self):
        self.assertItemsEqual(
            [
                ("http://host", ("trusty", "main")),
                ("http://host", ("trusty", "restricted")),
            ],
            self.driver.parse_urls(
                ["http://host/dists/ trusty main restricted"]
            )
        )
        self.assertItemsEqual(
            [("http://host", ("trusty", "main"))],
            self.driver.parse_urls(
                ["http://host/dists trusty main"]
            )
        )
        self.assertItemsEqual(
            [("http://host", ("trusty", "main"))],
            self.driver.parse_urls(
                ["http://host/ trusty main"]
            )
        )
        self.assertItemsEqual(
            [
                ("http://host", ("trusty", "main")),
                ("http://host2", ("trusty", "main")),
            ],
            self.driver.parse_urls(
                [
                    "http://host/ trusty main",
                    "http://host2/dists/ trusty main",
                ]
            )
        )

    def test_parse_urls_fail_if_invalid(self):
        with self.assertRaisesRegexp(ValueError, "Invalid url:"):
            next(self.driver.parse_urls(["http://host/dists/trusty main"]))
        with self.assertRaisesRegexp(ValueError, "Invalid url:"):
            next(self.driver.parse_urls(["http://host/dists trusty,main"]))


class TestDebIndexWriter(base.TestCase):
    def setUp(self):
        super(TestDebIndexWriter, self).setUp()
        self.writer = deb_driver.DebIndexWriter(
            Context(),
            "x86_64"
        )

