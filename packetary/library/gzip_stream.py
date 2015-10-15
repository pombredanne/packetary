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

import zlib

from . import stream

class GzipDecompress(stream.Stream):
    """The decompress stream."""

    def __init__(self, fileobj):
        super(GzipDecompress, self).__init__(fileobj)
        # Magic parameter makes zlib module understand gzip header
        # http://stackoverflow.com/questions/1838699/how-can-i-decompress-a-gzip-stream-with-zlib
        # This works on cpython and pypy, but not jython.
        self.decompress = zlib.decompressobj(16 + zlib.MAX_WBITS)

    def _read(self):
        chunk = self.fileobj.read(self.chunk_size)
        if chunk == "":
            return self.decompress.flush()
        return self.decompress.decompress(chunk)
