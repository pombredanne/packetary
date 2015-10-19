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

from packetary.library.connections import ConnectionsPool
from packetary.library.executor import ExecutionScope
from packetary.library.executor import Executor


class Context(object):

    def __init__(self, options):
        self.executor = Executor(options)
        self.connections = ConnectionsPool(options)
        self.ignore_errors = options.get('ignore_errors', 0)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.shutdown()

    def create_scope(self, ignore_errors=None):
        """Gets the execution scope"""
        if ignore_errors is None:
            ignore_errors = self.ignore_errors

        return ExecutionScope(self.executor, ignore_errors)

    def shutdown(self, wait=True):
        """Stops the execution."""
        self.executor.shutdown(wait)
