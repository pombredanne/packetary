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

import abc
import signal

from cliff import command
import six

from packetary.api import create_context
from packetary.cli.commands.utils import read_lines_from_file


@six.add_metaclass(abc.ABCMeta)
class BaseRepoCommand(command.Command):
    def get_parser(self, prog_name):
        parser = super(BaseRepoCommand, self).get_parser(prog_name)
        parser.add_argument(
            '-t',
            '--type',
            type=str,
            choices=['deb', 'yum'],
            metavar='DISTRIBUTION',
            default='deb',
            help='The type of distribution.')

        parser.add_argument(
            '-a',
            '--arch',
            type=str,
            choices=["x86_64", "i386"],
            metavar='ARCHITECTURE',
            default="x86_64",
            help='The target architecture.')

        origin_gr = parser.add_mutually_exclusive_group(required=True)
        origin_gr.add_argument(
            '-o', '--origin-url',
            nargs="+",
            dest='origins',
            type=six.text_type,
            metavar='URL',
            help='Space separated list of urls for origin repositories.')

        origin_gr.add_argument(
            '-O', '--origin-file',
            type=read_lines_from_file,
            dest='origins',
            metavar='FILENAME',
            help='The path to file with urls for origin repositories.')

        return parser

    def take_action(self, parsed_args):
        """See the Command.take_action.

        :return: the result of take_repo_action
        :rtype: object
        """
        with create_context(**self.app_args.__dict__) as context:
            signal.signal(signal.SIGTERM, lambda *_: context.shutdown(False))
            return self.take_repo_action(
                context,
                parsed_args
            )

    @abc.abstractmethod
    def take_repo_action(self, context, parsed_args):
        """Takes action on repository.

        :return: the action result
        """


class BaseProduceOutputCommand(BaseRepoCommand):
    columns = ()

    def get_parser(self, prog_name):
        parser = super(BaseProduceOutputCommand, self).get_parser(prog_name)

        group = parser.add_argument_group(
            title='output formatter',
            description='output formatter options',
        )
        group.add_argument(
            '-c', '--column',
            nargs='+',
            choices=self.columns,
            dest='columns',
            metavar='COLUMN',
            default=[],
            help='Space separated list of columns to include.',
        )
        group.add_argument(
            '-s',
            '--sort-columns',
            type=str,
            nargs='+',
            choices=self.columns,
            metavar='SORT_COLUMN',
            default=[self.columns[0]],
            help='Space separated list of keys for sorting '
                 'the data.'
        )
        group.add_argument(
            '--sep',
            type=six.text_type,
            metavar='ROW SEPARATOR',
            default=six.text_type('; '),
            help='The row separator.'
        )

        return parser

    def produce_output(self, parsed_args, data):
        indexes = dict(
            (c, i) for i, c in enumerate(self.columns)
        )
        sort_index = [indexes[c] for c in parsed_args.sort_columns]
        if isinstance(data, list):
            data.sort(key=lambda x: [x[i] for i in sort_index])
        else:
            data = sorted(data, key=lambda x: [x[i] for i in sort_index])

        if parsed_args.columns:
            include_index = [
                indexes[c] for c in parsed_args.columns
            ]
            data = ((row[i] for i in include_index) for row in data)
            columns = parsed_args.columns
        else:
            columns = self.columns

        stdout = self.app.stdout
        sep = parsed_args.sep

        # header
        stdout.write("# ")
        stdout.write(sep.join(columns))
        stdout.write("\n")

        for row in data:
            stdout.write(sep.join(row))
            stdout.write("\n")

    def run(self, parsed_args):
        # Use custom output producer, because the
        # cliff.lister with default formatters does not work
        # with large arrays of data
        # TODO(custom formatter)
        data = self.take_action(parsed_args)
        self.produce_output(parsed_args, data)
        return 0

    @abc.abstractmethod
    def take_repo_action(self, driver, parsed_args):
        """See Command.take_action."""
