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
import yaml

from fuelclient.client import APIClient
from fuelclient.objects import FuelVersion
from packetary.api import create_context


class Application(app.App):
    """Main cliff application class.

    Performs initialization of the command manager and
    configuration of basic engines.
    """

    config = None
    versions = None
    sources  = None
    packetary_context = None

    def build_option_parser(self, description, version, argparse_kwargs=None):
        """Overrides default options for backwards compatibility."""
        p_inst = super(Application, self)
        parser = p_inst.build_option_parser(description=description,
                                            version=version,
                                            argparse_kwargs=argparse_kwargs)

        parser.add_argument(
            "--config",
            default="/etc/fuel-createmirror/config.yaml",
            metavar="PATH",
            help="Path to config file."
        )
        parser.add_argument(
            "--fuel",
            metavar="FUEL-SERVER",
            help="The Fuel-backend`s version."
        )
        parser.add_argument(
            "-p", "--password",
            required=True,
            help="The Fuel-backend`s password."
        )
        return parser

    def initialize_app(self, argv):
        with open(self.options.config, "r") as stream:
            config = yaml.parse(stream)

        fuel_ver = FuelVersion.get_all_data()

        self.config = config['common']
        self.config.setdefault("localurl", self.config["fuel"])
        self.versions = config["versions"]
        self.versions['mos_version'] = fuel_ver['release']
        self.versions['openstack_version'] = fuel_ver['openstack_version']
        self.sources = config['sources']

        APIClient.root = self.options.fuel or self.config['fuel']
        APIClient.password = self.options.password

        self.packetary_context = create_context(
            thread_count=self.config['thread_count'],
            thread_count=self.config['ignore_error_count'],
            connection_count=self.config['ignore_error_count'],
            connection_proxy=self.config['http_proxy'],
            connection_secure_proxy=self.config['https_proxy'],
        )


def main(argv=None):
    return Application(
        description="The packages management tool.",
        version="0.0.1",
        command_manager=CommandManager("packetary", convert_underscores=True)
    ).run(argv)


def test(name, cmd_class, argv=None):
    """Helps to debug command."""
    import sys

    if argv is None:
        argv = sys.argv[1:]

    argv = [name] + argv + ["-v", "-v", "--debug"]
    cmd_mgr = CommandManager("test_fuel_mirror", convert_underscores=True)
    cmd_mgr.add_command(name, cmd_class)
    return Application(
        description="The fuel mirror utility test.",
        version="0.0.1",
        command_manager=cmd_mgr
    ).run(argv)
