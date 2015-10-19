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

import logging
import os
import six
import six.moves.urllib.request as urllib_request
import six.moves.urllib_error as urllib_error

from packetary.library.streams import BufferedStream


logger = logging.getLogger(__package__)


class RangeError(urllib_error.URLError):
    pass


class RetryableRequest(urllib_request.Request):
    offset = 0
    retries = 1


class RetryableResponse(BufferedStream):
    def __init__(self, request, response, opener):
        super(RetryableResponse, self).__init__(response)
        self.request = request
        self.opener = opener

    def _read(self):
        while 1:
            try:
                chunk = self.fileobj.read(self.chunk_size)
                self.request.offset += len(chunk)
                return chunk
            except IOError as e:
                response = self.opener.error(
                    self.request.get_type(), self.request,
                    self.fileobj, 502, str(e), self.fileobj.info()
                )
                self.fileobj = response.fileobj


class RetryHandler(urllib_request.BaseHandler):
    @staticmethod
    def http_request(request):
        logger.debug("start request: %s", request.get_full_url())
        if request.offset > 0:
            request.add_header('Range', 'bytes=%d-' % request.offset)
        return request

    def http_response(self, request, response):
        # the server should response partial content if range is specified
        logger.debug(
            "finish request: %s - %d (%s)",
            request.get_full_url(), response.getcode(), response.msg
        )
        if request.offset > 0 and response.getcode() != 206:
            raise RangeError("The server does not support ranges.")
        return RetryableResponse(request, response, self.parent)

    def http_error(self, req, fp, code, msg, hdrs):
        if code >= 500 and req.retries > 0:
            req.retries -= 1
            logger.warning(
                "retry: %s, %d %s [%d]",
                req.get_full_url(), code, msg, req.retry_number
            )
            return self.parent.open(req)

    https_request = http_request
    https_response = http_response


class Connection(object):
    def __init__(self, opener, retries):
        self.opener = opener
        self.retries = retries

    def get_request(self, url, offset=0):
        if url.startswith("/"):
            url = "file://" + url

        request = RetryableRequest(url)
        request.retries = self.retries
        request.offset = offset
        return request

    def open_stream(self, url, offset=0):
        request = self.get_request(url, offset)
        while 1:
            try:
                return self.opener.open(request)
            except urllib_error.HTTPError:
                raise
            except IOError as e:
                if request.retries < 0:
                    raise
                logger.error(
                    "Failed to open url: %s. retries left(%d)",
                    str(e), request.retries
                )
                request.retries -= 1

    @staticmethod
    def _ensure_dir_exists(dst):
        target_dir = os.path.dirname(dst)
        try:
            os.makedirs(target_dir)
        except OSError as e:
            if e.errno != 17:
                raise

    def _copy_stream(self, fd, url, offset):
        os.ftruncate(fd, offset)
        os.lseek(fd, offset, os.SEEK_SET)
        source = self.open_stream(url, offset)
        chunk_size = 16 * 1024
        while 1:
            chunk = source.read(chunk_size)
            if not chunk:
                break
            os.write(fd, chunk)

    def retrieve(self, url, filename, offset=0):
        self._ensure_dir_exists(filename)
        fd = os.open(filename, os.O_CREAT | os.O_WRONLY)
        try:
            self._copy_stream(fd, url, offset)
        except RangeError:
            if offset == 0:
                raise
            logger.warning(
                "Failed to resume download, starts from begin: %s", url
            )
            self._copy_stream(fd, url, 0)
        finally:
            os.fsync(fd)
            os.close(fd)


class ConnectionContext(object):
    def __init__(self, connection, pool):
        self.connection = connection
        self.pool = pool

    def __enter__(self):
        return self.connection

    def __exit__(self, *_):
        self.pool.release(self.connection)


class ConnectionsPool(object):
    def __init__(self, options):
        retries = options.get("retries_count", 0)
        if "connection_proxy" in options:
            proxies = {
                "http_proxy": options["connection_proxy"],
                "https_proxy": options["connection_proxy"],
            }
        else:
            proxies = None

        opener = urllib_request.build_opener(
            RetryHandler(),
            urllib_request.ProxyHandler(proxies)
        )

        limit = max(options.get("connection_count", 1), 1)
        pool = six.moves.queue.Queue()
        while limit > 0:
            pool.put(Connection(opener, retries))
            limit -= 1

        self.pool = pool

    def acquire(self):
        return ConnectionContext(self.pool.get(), self)

    def release(self, connection):
        self.pool.put(connection)
