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

from packetary.cli.commands import mirror
from packetary.cli.commands import packages
from packetary.cli.commands import unresolved
from packetary.tests import base


def mock_factory(*args, **kwargs):
    m = mock.MagicMock()
    # store the arguments
    m(*args, **kwargs)
    return m


@mock.patch.multiple(
    "packetary.library.context",
    ConnectionsPool=mock_factory,
)
class TestCliCommands(base.TestCase):
    common_argv = [
        "--ignore-error-count=3",
        "--thread-count=8",
        "--connection-count=4",
        "--retry-count=10",
        "--connection-proxy=http://proxy",
        "--connection-secure-proxy=https://proxy"
    ]

    mirror_argv = [
        "-o", "http://localhost/origin",
        "-d", ".",
        "-r", "http://localhost/requires",
        "-b", "test-package",
        "-t", "deb",
        "-a", "x86_64",
        "--clean",
    ]

    packages_argv = [
        "-o", "http://localhost/origin",
        "-t", "deb",
        "-a", "x86_64"
    ]

    unresolved_argv = [
        "-o", "http://localhost/origin",
        "-t", "deb",
        "-a", "x86_64"
    ]

    def start_cmd(self, cmd, argv):
        cmd.debug(argv + self.common_argv)

    def check_context(self, context):
        self.assertEqual(3, context.ignore_errors_num)
        self.assertEqual(8, context.thread_count)
        context.connections.assert_called_once_with(
            count=4,
            retries_num=10,
            proxy="http://proxy",
            secure_proxy="https://proxy",
        )

    @mock.patch("packetary.cli.commands.mirror.createmirror")
    def test_mirror_cmd(self, createmirror):
        self.start_cmd(mirror, self.mirror_argv)
        createmirror.assert_called_once_with(
            mock.ANY, "deb", "x86_64", ".",
            ["http://localhost/origin"],
            ["http://localhost/requires"],
            ["test-package"],
            False
        )
        self.check_context(createmirror.call_args[0][0])

    @mock.patch("packetary.cli.commands.packages.get_packages")
    def test_get_packages_cmd(self, get_packages):
        self.start_cmd(packages, self.packages_argv)
        get_packages.assert_called_once_with(
            mock.ANY, "deb", "x86_64",
            ["http://localhost/origin"],
            mock.ANY
        )
        self.check_context(get_packages.call_args[0][0])

    @mock.patch("packetary.cli.commands.unresolved.get_unresolved_depends")
    def test_get_unresolved_cmd(self, get_unresolved_depends):
        self.start_cmd(unresolved, self.unresolved_argv)
        get_unresolved_depends.assert_called_once_with(
            mock.ANY, "deb", "x86_64",
            ["http://localhost/origin"],
            mock.ANY
        )
        self.check_context(get_unresolved_depends.call_args[0][0])
