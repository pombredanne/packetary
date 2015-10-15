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
from cliff import display
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


class BaseListCommand(display.DisplayCommandBase, BaseCommand):
    columns = ()

    @property
    def formatter_namespace(self):
        return 'cliff.formatter.show'

    @property
    def formatter_default(self):
        return 'value'

    def get_parser(self, prog_name):
        parser = super(BaseListCommand, self).get_parser(prog_name)

        # Add sorting key argument to the output formatters group
        # if it exists. If not -- add is to the general group.
        matching_groups = (
            x for x in getattr(parser, '_action_groups', [])
            if x.title == 'output formatters'
        )

        group = next(matching_groups, parser)

        group.add_argument('-s',
                           '--sort-columns',
                           type=str,
                           nargs='+',
                           choices=self.columns,
                           metavar='SORT_COLUMN',
                           default=[self.columns[0]],
                           help='Space separated list of keys for sorting '
                                'the data. Defaults to id. Wrong values '
                                'are ignored.')

        # Monkey patch the columns argument
        matching_actions = (
            x for x in getattr(group, '_actions') if x.dest == 'columns'
        )

        action = next(matching_actions, None)
        if action is not None:
            action.choices = self.columns

        return parser

    def produce_output(self, parsed_args, column_names, data):
        indexes = [column_names.index(c) for c in parsed_args.sort_columns]
        data.sort(key=lambda x: [x[i] for i in indexes])
        if parsed_args.columns:
            columns_to_include = [c for c in column_names
                                  if c in parsed_args.columns]
            # Set up argument to compress()
            selector = [(c in columns_to_include)
                        for c in column_names]
            data = self._compress_iterable(data, selector)

        # TODO implement custom formatter
        # The table formatter is not able to print
        # large array of data.
        # Use direct print to stdout instead
        stdout = self.app.stdout
        for row in data:
            stdout.write(six.text_type("; ").join(row))
            stdout.write("\n")

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
    def take_action_in_context(self, context, parsed_args):
        """Takes action within context."""

    def take_action(self, parsed_args):
        """See Command.take_action."""
        context = Context(self.app_args.__dict__)
        signal.signal(signal.SIGTERM, lambda *_: context.shutdown(False))
        try:
            return self.take_action_in_context(context, parsed_args)
        finally:
            context.shutdown()
