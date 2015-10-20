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

from packetary.library import connections
from packetary.tests import base


class TestConnectionsPool(base.TestCase):
    def test_get_connection(self):
        pool = connections.ConnectionsPool({"connection_count": 2})
        self.assertEqual(2, pool.free.qsize())
        with pool.get():
            self.assertEqual(1, pool.free.qsize())
        self.assertEqual(2, pool.free.qsize())

    def test_set_proxy(self):
        pool = connections.ConnectionsPool({
            "connection_count": 1,
            "connection_proxy": "http://10.250.1.1",
        })
        with pool.get() as c:
            for h in c.opener.handlers:
                if isinstance(h, connections.urllib_request.ProxyHandler):
                    self.assertEqual(
                        "http://10.250.1.1", h.proxies["http"]
                    )
                    break
            else:
                self.fail("ProxyHandler should be in list of handlers.")

    def test_reliability(self):
        pool = connections.ConnectionsPool({
            "connection_count": 0,
            "retries_count": 2
        })
        self.assertEqual(1, pool.free.qsize())
        with pool.get() as c:
            self.assertEqual(2, c.retries)
            for h in c.opener.handlers:
                if isinstance(h, connections.RetryHandler):
                    break
            else:
                self.fail("RetryHandler should be in list of handlers.")


class TestConnection(base.TestCase):
    def setUp(self):
        super(TestConnection, self).setUp()
        self.connection = connections.Connection(mock.MagicMock(), 2)

    def test_get_request(self):
        request = self.connection.get_request("/test/file", 0)
        self.assertIsInstance(request, connections.RetryableRequest)
        self.assertEqual("file:///test/file", request.get_full_url())
        self.assertEqual(0, request.offset)
        self.assertEqual(2, request.retries)
        request2 = self.connection.get_request("http://server/path", 100)
        self.assertEqual("http://server/path", request2.get_full_url())
        self.assertEqual(100, request2.offset)

    def test_open_stream(self):
        self.connection.open_stream("/test/file")
        args = self.connection.opener.open.args
        print(args)
        self.assertEqual(1, self.connection.opener.open.call_count)
