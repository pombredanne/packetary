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

from cliff import app
from cliff.commandmanager import CommandManager


class Application(app.App):
    """Main cliff application class.

    Performs initialization of the command manager and
    configuration of basic engines.
    """

    def build_option_parser(self, description, version, argparse_kwargs=None):
        """Overrides default options for backwards compatibility."""
        p_inst = super(Application, self)
        parser = p_inst.build_option_parser(description=description,
                                            version=version,
                                            argparse_kwargs=argparse_kwargs)

        parser.add_argument(
            "--ignore-error-count",
            type=int,
            default=2,
            metavar="NUMBER",
            help="The number of errors that can be ignored."
        )
        parser.add_argument(
            "--retry-count",
            type=int,
            default=5,
            metavar="NUMBER",
            help="The number of retries."
        )
        parser.add_argument(
            "--thread-count",
            default=3,
            type=int,
            metavar="NUMBER",
            help="The number of threads."
        )
        parser.add_argument(
            "--connection-count",
            default=2,
            type=int,
            metavar="NUMBER",
            help="The number of simultaneous connections."
        )
        parser.add_argument(
            "--connection-proxy",
            default=None,
            metavar="http://username:password@proxy_host:proxy_port",
            help="The http proxy url."
        )
        parser.add_argument(
            "--connection-secure-proxy",
            default=None,
            metavar="https://username:password@proxy_host:proxy_port",
            help="The https proxy url."
        )
        return parser


def main(argv=None):
    return Application(
        description="The packages management tool.",
        version="0.0.1",
        command_manager=CommandManager("packetary", convert_underscores=True)
    ).run(argv)


def debug(name, cmd_class, argv=None):
    """Helps to debug command."""
    import sys

    if argv is None:
        argv = sys.argv[1:]

    argv = [name] + argv + ["-v", "-v", "--debug"]
    cmd_mgr = CommandManager("test_packetary", convert_underscores=True)
    cmd_mgr.add_command(name, cmd_class)
    return Application(
        description="The packages management tool test.",
        version="0.0.1",
        command_manager=cmd_mgr
    ).run(argv)
