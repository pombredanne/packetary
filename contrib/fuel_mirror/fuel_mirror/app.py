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

import os

from cliff import app
from cliff.commandmanager import CommandManager
import yaml


import fuel_mirror
from fuel_mirror.common import accessors


class Application(app.App):
    """Main cliff application class.

    Performs initialization of the command manager and
    configuration of basic engines.
    """

    config = None
    fuel = None
    packetary = None
    sources = None
    versions = None

    def build_option_parser(self, description, version, argparse_kwargs=None):
        """Overrides default options for backwards compatibility."""
        p_inst = super(Application, self)
        parser = p_inst.build_option_parser(description=description,
                                            version=version,
                                            argparse_kwargs=argparse_kwargs)

        parser.add_argument(
            "--config",
            default="/etc/fuel-mirror/config.yaml",
            metavar="PATH",
            help="Path to config file."
        )
        parser.add_argument(
            "-S", "--fuel-server",
            metavar="FUEL-SERVER",
            help="The public address of Fuel Master."
        )
        parser.add_argument(
            "-P", "--fuel-password",
            help="Fuel Master admin password (defaults to admin)."
                 " Alternatively, use env var KEYSTONE_PASSWORD)."
        )
        return parser

    def initialize_app(self, argv):
        with open(self.options.config, "r") as stream:
            config = yaml.load(stream)

        self.config = config['common']
        self.versions = config["versions"]
        self.sources = config['sources']
        self.fuel = accessors.FuelObjectsAccessor(
            self.options.fuel_address or self.config['fuel_server'],
            self.options.fuel_password
        )
        fuel_ver = self.fuel.FuelVersion.get_all_data()
        self.versions['mos_version'] = fuel_ver['release']
        self.versions['openstack_version'] = fuel_ver['openstack_version']

        self.packetary = accessors.PacketaryAPIAccessor(
            thread_count=int(self.config.get('thread_count', 0)),
            retry_count=int(self.config.get('retry_count', 0)),
            ignore_error_count=int(self.config.get('ignore_error_count', 0)),
            connection_count=int(self.config.get('connection_count', 0)),
            connection_proxy=self.config.get('http_proxy'),
            connection_secure_proxy=self.config.get('https_proxy'),
        )


def main(argv=None):
    return Application(
        description="The packages management tool.",
        version=fuel_mirror.__version__,
        command_manager=CommandManager("packetary", convert_underscores=True)
    ).run(argv)


def debug(name, cmd_class, argv=None):
    """Helps to debug command."""
    import sys

    if argv is None:
        argv = sys.argv[1:]

    argv = [name] + argv + [
        "-v", "-v", "--debug", '-P', "admin",
        "--config",
        os.path.join(os.path.dirname(__file__), "..", "etc", "config.yaml")]

    cmd_mgr = CommandManager("test_fuel_mirror", convert_underscores=True)
    cmd_mgr.add_command(name, cmd_class)
    return Application(
        description="The fuel mirror utility test.",
        version="0.0.1",
        command_manager=cmd_mgr
    ).run(argv)
