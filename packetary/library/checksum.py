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



import hashlib


def _checksum(method):
    """Gets the function to calculate checksum,
    with selected method.
    """

    def calc(f):
        s = method()
        with open(f, "rb") as stream:
            while True:
                chunk = stream.read(1024)
                if not chunk:
                    break
                s.update(chunk)
        return s.hexdigits()
    return calc


md5 = _checksum(hashlib.md5)

sha1 = _checksum(hashlib.sha1)

sha256 = _checksum(hashlib.sha256)
