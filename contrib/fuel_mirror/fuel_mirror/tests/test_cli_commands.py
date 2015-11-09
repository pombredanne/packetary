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
import subprocess

# The cmd2 does not work with python3.5
# because it tries to get access to the property mswindows,
# that was removed in 3.5
subprocess.mswindows = False

from fuel_mirror.commands import apply
from fuel_mirror.commands import create
from fuel_mirror.commands import update
from fuel_mirror.tests import base


@mock.patch.multiple(
    "fuel_mirror.app",
    accessors=mock.DEFAULT,
    yaml=mock.DEFAULT,
    open=mock.DEFAULT
)
class TestCliCommands(base.TestCase):
    common_argv = [
        "--config=/etc/fuel-mirror/config.yaml",
        "--fuel-server=10.25.0.2",
        "--fuel-user=test",
        "--fuel-password=test1"
    ]

    apply_argv = [
        "--default",
        "--env 1"
    ]

    create_argv = [
        "--full", "--no-apply", "--default"
    ]

    update_argv = [
        "-U"
    ]

    def start_cmd(self, cmd, argv):
        cmd.debug(argv + self.common_argv)

    def test_create_cmd(self, accessors, yaml, open):
        yaml.load.return_value = _DEFAULT_CONFIG
        self.start_cmd(create, self.create_argv)
        open.assert_called_once_with(
            "/etc/fuel-mirror/config.yaml", "r"
        )
        yaml.load.assert_called_once_with(open().__enter__())
        accessors.get_packetary_accessor.assert_called_once_with(
            thread_count=1,
            ignore_error_count=2,
            retries_count=3,
            http_proxy="http://localhost",
            https_proxy="https://localhost",
        )
        packetary = accessors.get_packetary_accessor()
        packetary.assert_any_call("yum", "x86_64")
        packetary.assert_any_call("deb", "x86_64")
        self.assertEqual(2, packetary.call_count)

    def test_update_cmd(self, accessor, yaml, open):
        self.start_cmd(create, self.create_argv)

    def test_applyd_cmd(self, accessor, yaml, open):
        self.start_cmd(create, self.create_argv)


_DEFAULT_CONFIG = {
    "common": {
        "thread_count": 1,
        "ignore_error_count": 2,
        "retries_count": 3,
        "http_proxy": "http://localhost",
        "https_proxy": "https://localhost",
        "target_dir": "/var/www/nailgun"
    },
    "versions": {
        "centos_version": "1",
        "ubuntu_version": "2"
    },

    "sources": [
        {
            "name": "mos",
            "osname": "ubuntu",
            "type": "deb",
            "baseurl": "http://localhost/mos/{ubuntu_version}",
            "repositories": [
                "mos main",
            ],
        },
        {
            "name": "mos",
            "osname": "centos",
            "type": "yum",
            "baseurl": "http://localhost/mos/{centos_version}",
            "repositories": [
                "os"
            ],
        },
        {
            "name": "ubuntu",
            "osname": "ubuntu",
            "type": "deb",
            "master": "mos",
            "baseurl": "http://localhost/ubuntu",
            "repositories": [
                "{ubuntu_version} main"
            ],
            "bootstrap": [
               "ubuntu-minimal"
            ]
        },
        {
            "name": "centos",
            "osname": "centos",
            "type": "yum",
            "master": "mos",
            "baseurl": "http://localhost/centos/{centos_version}",
            "repositories": [
                "os"
            ]
        }
    ]
}
