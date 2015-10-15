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

from packetary.commands.base import BaseListCommand
from packetary.commands.base import MakeContextMixin
from packetary.library.index import Index


class ListUnresolved(MakeContextMixin, BaseListCommand):
    columns = (
        "package",
        "version",
        "choice",
    )

    def take_action_in_context(self, context, parsed_args):
        repo = context.create_repository(parsed_args.type, parsed_args.arch)
        index = Index()
        repo.load(parsed_args.url, index.add)
        format_obj = self.format_object
        unresolved = [
            format_obj(parsed_args.columns, x)
            for x in index.get_unresolved()
        ]
        return self.columns, unresolved


if __name__ == "__main__":
    from packetary.app import test
    test("unresolved", ListUnresolved, ["unresolved", "-u", "http://mirror.yandex.ru/centos/7.1.1503/updates", "-t", "yum", '-v', '-v', '--debug'])
    # test("unresolved", ListUnresolved, ["unresolved", "-u", "http://mirror.yandex.ru/ubuntu/dists trusty-updates main", "-t", "deb", '-v', '-v', '--debug'])
