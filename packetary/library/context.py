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
from packetary.library.executor import AsynchronousSection


class Context(object):

    DEFAULT_THREADS_COUNT = 1
    DEFAULT_BACKLOG_SIZE = 100

    def __init__(self, **kwargs):
        self.connections = ConnectionsPool(
            count=kwargs.get("connection_count", 0),
            retries_num=kwargs.get("retry_count", 0),
            proxy=kwargs.get("connection_proxy"),
            secure_proxy=kwargs.get("connection_secure_proxy")
        )
        self.ignore_errors_num = kwargs.get('ignore_error_count', 0)
        self.thread_count = kwargs.get(
            'thread_count', self.DEFAULT_BACKLOG_SIZE
        )

    def async_section(self, ignore_errors_num=None):
        """Gets the execution scope"""
        if ignore_errors_num is None:
            ignore_errors_num = self.ignore_errors_num

        return AsynchronousSection(self.thread_count, ignore_errors_num)
