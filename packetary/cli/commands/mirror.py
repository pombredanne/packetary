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

import six

from packetary.api import createmirror
from packetary.cli.commands.base import BaseRepoCommand
from packetary.cli.commands.utils import read_lines_from_file


class CreateMirror(BaseRepoCommand):
    def get_parser(self, prog_name):
        parser = super(CreateMirror, self).get_parser(prog_name)

        parser.add_argument(
            "-d",
            "--destination",
            required=True,
            help="The destination folder."
        )
        requires_gr = parser.add_mutually_exclusive_group(required=False)
        requires_gr.add_argument(
            '-r', '--requires-url',
            nargs="+",
            dest='requires',
            type=six.text_type,
            metavar='URL',
            help='Space separated list of urls for origin repositories.')

        requires_gr.add_argument(
            '-R', '--requires-file',
            type=read_lines_from_file,
            dest='requires',
            metavar='FILENAME',
            help='The path to file with urls for origin repositories.')
        return parser

    def take_repo_action(self, driver, parsed_args):
        packages_count = createmirror(
            driver,
            parsed_args.destination,
            parsed_args.origins,
            parsed_args.requires
        )
        self.app.stdout.write("Packages copied: %d.\n" % packages_count)


if __name__ == "__main__":
    from packetary.cli.app import test
    test("mirror", CreateMirror, [
        "mirror", "-o", "http://mirror.yandex.ru/ubuntu/dists trusty main", "-t", "deb", '-v', '-v', '--debug',
        "-r", "http://mirror.yandex.ru/ubuntu/dists trusty-updates main", "-d", "../mirror/ubuntu"
    ])
    # test("mirror", CreateMirror, [
    #     "mirror", "-O", "../../mirror/centos.txt", "-t", "yum", '-v', '-v', '--debug',
    #     "-r", "http://mirror.fuel-infra.org/mos-repos/centos/mos8.0-centos6-fuel/os", "-d", "../../mirror/centos"
    # ])
