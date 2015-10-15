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


class Stream(object):
    """Stream object."""
    chunk_size = 1024

    def __init__(self, fileobj):
        self.fileobj = fileobj
        self.buffer = ''

    def __getattr__(self, item):
        return getattr(self.fileobj, item)

    def _read_buffer(self):
        tmp = self.buffer
        self.buffer = ''
        return tmp

    def _align_chunk(self, chunk, size):
        self.buffer = chunk[size:]
        return chunk[:size]

    def _read(self):
        return self.fileobj.read(self.chunk_size)

    def read(self, size=-1):
        result = self._read_buffer()
        if size < 0:
            while True:
                chunk = self._read()
                if not chunk:
                    break
                result += chunk
        else:
            if len(result) > size:
                result = self._align_chunk(result, size)
            size -= len(result)
            while size > 0:
                chunk = self._read()
                if not chunk:
                    break
                if len(chunk) > size:
                    chunk = self._align_chunk(chunk, size)
                size -= len(chunk)
                result += chunk
        return result

    def readline(self):
        pos = self.buffer.find('\n')
        if pos >= 0:
            line = self._align_chunk(self.buffer, pos + 1)
        else:
            line = self._read_buffer()
            while True:
                chunk = self._read()
                if chunk == '':
                    break
                pos = chunk.find('\n')
                if pos >= 0:
                    line += self._align_chunk(chunk, pos + 1)
                    break
                line += chunk
        return line

    def readlines(self):
        while True:
            line = self.readline()
            if line == '':
                break
            yield line

    def __iter__(self):
        return self.readlines()
