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


@mock.patch("packetary.library.executor.logger")
class TestExecutor(base.TestCase):
    def setUp(self):
        super(TestExecutor, self).setUp()
        self.executor = executor.Executor({"threads_count": 2})

    def test_execute(self, logger):
        results = []

        def on_complete(e):
            results.append(e)

        def raise_error(*_):
            raise ValueError("error")

        self.executor.execute(lambda: None, on_complete)
        self.executor.execute(raise_error, on_complete)
        self.executor.execute(lambda: None, raise_error)
        self.executor.shutdown()
        logger.exception.assert_called_with(
            "Exception in callback: %s", "error"
        )

        self.assertEqual(2, len(results))
        self.assertIs(None, results[0])
        self.assertIsInstance(results[1], ValueError)

    def test_shutdown(self, logger):
        pass
