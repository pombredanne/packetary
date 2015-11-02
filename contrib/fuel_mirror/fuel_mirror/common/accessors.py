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

import functools
import os


def get_packetary_accessor(**kwargs):
    """Gets the configured repository manager."""

    import packetary

    return functools.partial(
        packetary.RepositoryManager.create,
        packetary.Context(packetary.Configuration(**kwargs))
    )


def get_fuel_api_accessor(fuel_address=None, fuel_password=None):
    """Gets the fuel client api accessor."""
    if fuel_address:
        host_and_port = fuel_address.split(":")
        os.environ["SERVER_ADDRESS"] = host_and_port[0]
        if len(host_and_port) > 1:
            os.environ["LISTEN_PORT"] = host_and_port[1]

    if fuel_password is not None:
        os.environ["KEYSTONE_USER"] = "admin"
        os.environ["KEYSTONE_PASS"] = fuel_password

    # import fuelclient.ClientAPI after configuring
    # environment variables
    from fuelclient import objects
    return objects
