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

from packetary.commands.base import BaseRepoCommand
from packetary.library.index import Index


class CreateMirror(BaseRepoCommand):
    def get_parser(self, prog_name):
        parser = super(CreateMirror, self).get_parser(prog_name)
        parser.add_argument(
            "-r",
            "--requires",
            action="append",
            help="The urls of repositories to resolve requirements."
        )
        parser.add_argument(
            "-d",
            "--destination",
            required=True,
            help="The destination folder."
        )
        return parser

    def take_repo_action(self, driver, parsed_args):
        packages = Index()
        driver.load(parsed_args.url, packages.add)
        if parsed_args.requires:
            requires = Index()
            driver.load(parsed_args.requires, requires.add)
            requires = requires.get_unresolved()
            if len(requires) == 0:
                self.app.stdout.write("Nothing to copy.\n")
                return
            packages = packages.resolve(requires)
        driver.clone(packages, parsed_args.destination)
        self.app.stdout.write("Operation completed successfully.\n")


if __name__ == "__main__":
    from packetary.app import test
    test("mirror", CreateMirror, [
        "mirror", "-u", "http://mirror.yandex.ru/ubuntu/dists trusty main", "-t", "deb", '-v', '-v', '--debug',
        "-r", "http://mirror.yandex.ru/ubuntu/dists trusty-updates main", "-d", "../mirror/ubuntu"
    ])
    # test("mirror", CreateMirror, [
    #     "mirror", "-u", "http://mirror.yandex.ru/centos/6.7/os", "-t", "yum", '-v', '-v', '--debug',
    #     "-r", "http://mirror.fuel-infra.org/mos-repos/centos/mos8.0-centos6-fuel/os", "-d", "../../mirror/centos"
    # ])
