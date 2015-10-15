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


from packetary.library import package
from packetary.tests import base


class TestVersionRange(base.TestCase):
    def __check_intersection(self, assertion, cases):
        for data in cases:
            v1 = package.VersionRange(*data[0])
            v2 = package.VersionRange(*data[1])
            assertion(
                v1.has_intersection(v2), msg="%s and %s" % (v1, v2)
            )
            assertion(
                v2.has_intersection(v1), msg="%s and %s" % (v2, v1)
            )

    def test_have_intersection(self):
        cases = [
            (("lt", 2), ("gt", 1)),
            (("lt", 3), ("lt", 4)),
            (("gt", 3), ("gt", 4)),
            (("eq", 1), ("eq", 1)),
            (("ge", 1), ("le", 1)),
            (("eq", 1), ("lt", 2)),
            ((None, None), ("le", 10)),
        ]
        self.__check_intersection(self.assertTrue, cases)

    def test_does_not_have_intersection(self):
        cases = [
            (("lt", 2), ("gt", 2)),
            (("ge", 2), ("lt", 2)),
            (("gt", 2), ("le", 2)),
            (("gt", 1), ("lt", 1)),
        ]
        self.__check_intersection(self.assertFalse, cases)

    def test_intersection_is_typesafe(self):
        with self.assertRaises(TypeError):
            package.VersionRange("eq", 1).has_intersection(("eq", 1))
