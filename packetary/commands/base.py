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

from cliff import command
import signal
import six

from packetary.library.context import Context
from packetary.library.context import repositories


@six.add_metaclass(abc.ABCMeta)
class BaseCommand(command.Command):
    def get_parser(self, prog_name):
        parser = super(BaseCommand, self).get_parser(prog_name)
        parser.add_argument(
            '-t',
            '--type',
            type=str,
            choices=repositories.types,
            metavar='DISTRIBUTION',
            default=sorted(repositories.types)[0],
            help='The type of distribution.')

        parser.add_argument(
            '-a',
            '--arch',
            type=str,
            choices=["x86_64", "i386"],
            metavar='ARCHITECTURE',
            default="x86_64",
            help='The target architecture.')

        parser.add_argument(
            '-u',
            '--url',
            type=str,
            metavar='URL',
            required=True,
            help='The repository URL.')

        return parser

    @abc.abstractmethod
    def take_action(self, parsed_args):
        """See the Command.take_action."""


class BaseProduceOutputCommand(BaseCommand):
    columns = ()

    @property
    def formatter_namespace(self):
        return 'cliff.formatter.show'

    @property
    def formatter_default(self):
        return 'value'

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
                 'the data. Defaults to id. Wrong values '
                 'are ignored.'
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
        # TODO write custom formatter, that supports data streaming
        data = self.take_action(parsed_args)
        self.produce_output(parsed_args, data)
        return 0

    @staticmethod
    def format_value(val):
        if not val:
            return six.text_type("-")
        if isinstance(val, list):
            return six.text_type(", ").join(six.text_type(x) for x in val)
        return six.text_type(val)

    def format_object(self, obj):
        return [self.format_value(getattr(obj, x)) for x in self.columns]

    @abc.abstractmethod
    def take_action(self, parsed_args):
        """See Command.take_action."""


@six.add_metaclass(abc.ABCMeta)
class MakeContextMixin(object):
    @abc.abstractmethod
    def take_action_with_context(self, context, parsed_args):
        """Takes action within context."""

    def take_action(self, parsed_args):
        """See Command.take_action."""
        context = Context(self.app_args.__dict__)
        signal.signal(signal.SIGTERM, lambda *_: context.shutdown(False))
        try:
            return self.take_action_with_context(context, parsed_args)
        finally:
            context.shutdown()
