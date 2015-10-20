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

import mock

from packetary.library import executor
from packetary.tests import base

import time


class TestExecutor(base.TestCase):
    def setUp(self):
        super(TestExecutor, self).setUp()
        self.executor = executor.Executor({"threads_count": 2})
        self.results = []

    def _on_complete(self, e):
        if e is None:
            self.results.append(e)
        else:
            self.results.append(str(e))

    def _raise_value_error(self, *_):
        raise ValueError("error")

    @mock.patch("packetary.library.executor.logger")
    def test_execute(self, logger):
        self.executor.execute(lambda: time.sleep(0), self._on_complete)
        self.executor.execute(self._raise_value_error, self._on_complete)
        self.executor.execute(lambda: time.sleep(0), self._raise_value_error)
        self.executor.shutdown()
        self.assertItemsEqual([None, 'error'], self.results)
        logger.exception.assert_called_with(
            "Exception in callback: %s", "error"
        )

    def _create_tasks_and_shutdown(self, wait):
        self.executor.execute(lambda: time.sleep(0.5), self._on_complete)
        self.executor.execute(lambda: time.sleep(0.5), self._on_complete)
        self.executor.execute(self._raise_value_error, self._on_complete)
        self.executor.shutdown(wait)

    def test_shutdown_with_wait(self):
        self._create_tasks_and_shutdown(True)
        self.assertItemsEqual([None, None, 'error'], self.results)

    def test_shutdown_without_wait(self):
        self._create_tasks_and_shutdown(False)
        self.assertNotIn("error", self.results)