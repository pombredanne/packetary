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


from packetary.library.index import Index

from packetary.tests import base
from packetary.tests.stubs.driver import package_generator
from packetary.tests.stubs.package import Relation
from packetary.tests.stubs.package import VersionRange


class TestIndex(base.TestCase):
    def test_add(self):
        index = Index()
        index.add(package_generator(
            version=1,
            provides_mask="provides-{0}",
            obsoletes_mask="obsoletes-{0}",
            requires_mask="requires-{0}",
        )[0])
        self.assertIn("package-0", index.packages)
        self.assertIn(1, index.packages["package-0"])
        self.assertIn("obsoletes-0", index.obsoletes)
        self.assertIn("provides-0", index.provides)

        index.add(package_generator(version=2)[0])
        self.assertEqual(1, len(index.packages))
        self.assertIn(1, index.packages["package-0"])
        self.assertIn(2, index.packages["package-0"])
        self.assertEqual(1, len(index.obsoletes))
        self.assertEqual(1, len(index.provides))

    def test_find_package(self):
        index = Index()
        p1 = package_generator(version=1)[0]
        p2 = package_generator(version=2)[0]
        index.add(p1)
        index.add(p2)

        self.assertIs(
            p1, index.find(Relation("package-0", VersionRange("eq", 1)))
        )
        self.assertIs(
            p2, index.find(Relation("package-0", VersionRange()))
        )
        self.assertIsNone(
            index.find(Relation("package-0", VersionRange("gt", 2)))
        )

    def test_find_newest_package(self):
        index = Index()
        p1, p2 = package_generator(count=2, version=2)
        p2.obsoletes.append(Relation(p1.name, VersionRange("lt", p1.version)))
        index.add(p1)
        index.add(p2)

        self.assertIs(
            p1, index.find(Relation(p1.name, VersionRange("eq", p1.version)))
        )
        self.assertIs(
            p2, index.find(Relation(p1.name, VersionRange("eq", 1)))
        )

    def test_find_obsolete(self):
        index = Index()
        p1 = package_generator(version=1, obsoletes_mask="obsoletes-{0}")[0]
        p2 = package_generator(version=2, obsoletes_mask="obsoletes-{0}")[0]
        index.add(p1)
        index.add(p2)

        self.assertIs(
            p2, index.find(Relation("obsoletes-0", VersionRange("eq", 1)))
        )
        self.assertIsNone(
            index.find(Relation("obsoletes-0", VersionRange("gt", 2)))
        )

    def test_find_provides(self):
        index = Index()
        p1 = package_generator(version=1, provides_mask="provides-{0}")[0]
        p2 = package_generator(version=2, provides_mask="provides-{0}")[0]
        index.add(p1)
        index.add(p2)

        self.assertIs(
            p2, index.find(Relation("provides-0", VersionRange("eq", 2)))
        )
        self.assertIsNone(
            index.find(Relation("provides-0", VersionRange("lt", 1)))
        )

    def test_len(self):
        index = Index()
        for p in package_generator(count=3, version=1):
            index.add(p)
        self.assertEqual(3, len(index))
        for p in package_generator(count=3, version=2):
            index.add(p)
        self.assertEqual(6, len(index))
        for p in package_generator(count=3, version=2):
            index.add(p)
        self.assertEqual(6, len(index))

    def test_resolve_with_master(self):
        master = Index()
        slave = Index()
        shared_package = package_generator(prefix="test")[0]
        shared_package.requires.append(Relation("unresolved"))
        master.add(shared_package)
        slave.add(shared_package)
        master.add(package_generator(
            prefix="test1", requires_mask="requires-{0}")[0]
        )
        required_package = package_generator(
            prefix="requires", requires_mask="test-{0}"
        )[0]
        slave.add(required_package)
        unresolved = master.get_unresolved()
        packages = slave.resolve(unresolved, master)
        self.assertItemsEqual([required_package], packages)
        self.assertEqual(1, len(unresolved))
        self.assertEqual("unresolved", unresolved.pop().name)

    def test_resolve(self):
        index = Index()
        index.add(package_generator(
            prefix="test1", requires_mask="requires-{0}")[0]
        )
        index.add(package_generator(
            prefix="test2", requires_mask="test1-{0}")[0]
        )
        index.add(package_generator(
            prefix="test3", requires_mask="requires-{0}")[0]
        )
        unresolved = set()
        unresolved.add(Relation("test2-0"))
        resolved = index.resolve(unresolved)
        self.assertItemsEqual(
            ["test2-0", "test1-0"],
            (x.name for x in resolved)
        )
        self.assertEqual(1, len(unresolved))
        self.assertEqual("requires-0", unresolved.pop().name)

    def test_get_unresolved(self):
        index = Index()
        index.add(
            package_generator(prefix="test1", requires_mask="requires-{0}")[0]
        )
        index.add(package_generator(
            prefix="test2", requires_mask="test1-{0}")[0]
        )
        package = package_generator(
            prefix="test3", requires_mask="requires-{0}"
        )[0]
        package.requires.append(Relation("requires-1"))
        index.add(package)
        unresolved = index.get_unresolved()
        self.assertEqual(2, len(unresolved))
        self.assertItemsEqual(
            ["requires-0", "requires-1"],
            [x.name for x in unresolved]
        )
