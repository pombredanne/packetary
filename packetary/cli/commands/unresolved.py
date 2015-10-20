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

from packetary.api import get_unresolved_depends
from packetary.cli.commands.base import BaseProduceOutputCommand
from packetary.cli.commands.utils import make_display_attr_getter


class ListUnresolved(BaseProduceOutputCommand):
    columns = (
        "package",
        "version",
        "choice",
    )

    def take_repo_action(self, context, parsed_args):
        return get_unresolved_depends(
            context,
            parsed_args.type,
            parsed_args.arch,
            parsed_args.origins,
            make_display_attr_getter(self.columns)
        )

if __name__ == "__main__":
    import sys

    from packetary.cli.app import test

    test(
        "unresolved",
        ListUnresolved,
        ["unresolved"] + sys.argv[1:] + ["-v", "-v", "--debug"]
    )
