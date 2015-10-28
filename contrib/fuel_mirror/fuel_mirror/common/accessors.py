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


class PacketaryAPIAccessor(object):
    """Packetary.api accessor."""
    def __init__(self, **kwargs):
        from packetary import api
        self.api = api
        self.context = api.create_context(**kwargs)

    def __getattr__(self, item):
        return functools.partial(getattr(self.api, item), self.context)


class FuelObjectsAccessor(object):
    """Fuelclient.Objects accessor."""

    def __init__(self, fuel_address=None, fuel_password=None):
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
        self.objects = objects

    def __getattr__(self, item):
        return getattr(self.objects, item)
