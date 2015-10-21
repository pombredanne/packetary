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
            "-d", "--destination",
            required=True,
            help="The destination folder."
        )
        parser.add_argument(
            "--keep-existing",
            action='store_true',
            default=False,
            help="Do not remove packages that does not exist in origin repo."
        )

        bootstrap_group = parser.add_mutually_exclusive_group(required=False)
        bootstrap_group.add_argument(
            "-b", "--bootstrap",
            nargs='+',
            dest='bootstrap',
            metavar='PACKAGE [OP VERSION]',
            type=six.text_type,
            help="Bootstrap package(s)."
        )
        bootstrap_group.add_argument(
            "-B", "--bootstrap-file",
            type=read_lines_from_file,
            dest='bootstrap',
            metavar='FILENAME',
            help="Bootstrap package(s)."
        )

        requires_group = parser.add_mutually_exclusive_group(required=False)
        requires_group.add_argument(
            '-r', '--requires-url',
            nargs="+",
            dest='requires',
            type=six.text_type,
            metavar='URL',
            help='Space separated list of urls for origin repositories.')

        requires_group.add_argument(
            '-R', '--requires-file',
            type=read_lines_from_file,
            dest='requires',
            metavar='FILENAME',
            help='The path to file with urls for origin repositories.')
        return parser

    def take_repo_action(self, context, parsed_args):
        """Overrides base class method."""
        packages_count = createmirror(
            context,
            parsed_args.type,
            parsed_args.arch,
            parsed_args.destination,
            parsed_args.origins,
            parsed_args.requires,
            parsed_args.bootstrap,
            parsed_args.keep_existing
        )
        self.app.stdout.write("Packages copied: %d.\n" % packages_count)


if __name__ == "__main__":
    import sys

    from packetary.cli.app import test

    test(
        "mirror",
        CreateMirror,
        ["mirror"] + sys.argv[1:] + ["-v", "-v", "--debug"]
    )
