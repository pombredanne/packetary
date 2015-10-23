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
from packetary.tests import base
# from packetary.cli.commands import unresolved
# from packetary.cli.commands import packages


class TestCli(base.TestCase):
    common_argv = [
        "--ignore-errors-count=3",
        "--thread-count=8",
        "--connection-count=4",
        "--retries-count=10",
        "--connection-proxy=http://proxy"
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

    def start_cmd(self, cmd, argv):
        cmd.debug(argv + self.common_argv)

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
