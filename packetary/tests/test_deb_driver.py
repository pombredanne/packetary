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

from packetary.library.drivers.deb_driver import Driver
from packetary.tests import base
from packetary.tests.stubs.context import Context


PACKAGES_GZ = os.path.join(os.path.dirname(__file__), "data", "packages.gz")


class TestDebDriver(base.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestDebDriver, cls).setUpClass()
        cls.driver = Driver(
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
    def test_load(self, logger):
        packages = []
        # connections = self.driver.connections
        # with open(PACKAGES_GZ, "rb") as stream:
        #     connections.open_stream.return_value = stream
        #     self.driver.load("http://host", ("trusty", "main"), packages.append)

        #open_stream.assert_called_once_with("")
        # asserts


#         suite, comp = repo
#         index_file = "{0}/dists/{1}/{2}/binary-{3}/Packages.gz".format(
#             baseurl, suite, comp, self.arch
#         )
#         logger.info("loading packages from: %s", index_file)
#         with self.connections.get() as connection:
#             stream = GzipDecompress(connection.open_stream(index_file))
#             pkg_iter = deb822.Packages.iter_paragraphs(stream)
#             for dpkg in pkg_iter:
#                 consumer(DebPackage(dpkg, baseurl, suite, comp))
#
#         logger.info(
#             "packages from %s has been loaded successfully.", index_file
#         )


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
#
#
# def create_index(self, destination):
#         return DebIndexWriter(self, destination)
#
#     def parse_urls(self, urls):
#         for url in urls:
#             try:
#                 baseurl, suite, comps = url.split(" ", 2)
#             except ValueError:
#                 raise ValueError(
#                     "Invalid url: {0}\n"
#                     "Expected: baseurl suite component[ component]"
#                     .format(url)
#                 )
#
#             if baseurl.endswith("/dists/"):
#                 baseurl = baseurl[:-7]
#             elif baseurl.endswith("/dists"):
#                 baseurl = baseurl[:-6]
#             elif baseurl.endswith("/"):
#                 baseurl = baseurl[:-1]
#
#             for comp in comps.split(":"):
#                 yield baseurl, (suite, comp)
#
#     def get_path(self, base, package):
#         baseurl = base or package.baseurl
#         return "/".join((baseurl, package.filename))
#
#     def load(self, baseurl, repo, consumer):
#         """Loads from Packages.gz."""
#         suite, comp = repo
#         index_file = "{0}/dists/{1}/{2}/binary-{3}/Packages.gz".format(
#             baseurl, suite, comp, self.arch
#         )
#         logger.info("loading packages from: %s", index_file)
#         with self.connections.get() as connection:
#             stream = GzipDecompress(connection.open_stream(index_file))
#             pkg_iter = deb822.Packages.iter_paragraphs(stream)
#             for dpkg in pkg_iter:
#                 consumer(DebPackage(dpkg, baseurl, suite, comp))
#
#         logger.info(
#             "packages from %s has been loaded successfully.", index_file
#         )
