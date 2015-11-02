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
import warnings

from packetary.repo_manager import RepositoryManager
from packetary.repo_manager import UnresolvedWarning
from packetary.repo_manager import Index
from packetary.tests import base
from packetary.tests.stubs import generator
from packetary.tests.stubs.driver import TestDriverAdapter


class TestRepositoryManager(base.TestCase):
    def test_get_unresolved_depends(self):
        index = Index()
        index.add(generator.gen_package(
            1, requires=generator.gen_relation("unresolved")))
        index.add(generator.gen_package(2, requires=None))
        index.add(generator.gen_package(
            3, requires=generator.gen_relation("package1")
        ))
        index.add(generator.gen_package(
            4,
            requires=generator.gen_relation("loop"),
            obsoletes=generator.gen_relation("loop", ["le", 1])
        ))

        unresolved = RepositoryManager._get_unresolved_depends(index)
        self.assertItemsEqual(
            ["loop", "unresolved"],
            (x.name for x in unresolved)
        )

    def test_get_minimal_subset_with_rdepends(self):
        index = Index()
        index.add(generator.gen_package(1, requires=None))
        index.add(generator.gen_package(2, requires=None))
        index.add(generator.gen_package(3, requires=None))
        index.add(generator.gen_package(
            4, requires=generator.gen_relation("package1")
        ))

        rdepends = Index()
        rdepends.add(generator.gen_package(1, requires=None))
        rdepends.add(generator.gen_package(
            5,
            requires=generator.gen_relation(
                "package10",
                alternative=generator.gen_relation("package4")[0]
            )
        ))

        unresolved = set(generator.gen_relation("package3"))
        resolved = RepositoryManager._get_minimal_subset(
            index, rdepends, unresolved
        )
        self.assertItemsEqual(
            ["package3", "package4"],
            (x.name for x in resolved)
        )
        self.assertEqual(0, len(unresolved))

    def test_get_minimal_subset_without_rdepends(self):
        index = Index()
        index.add(generator.gen_package(1, requires=None))
        index.add(generator.gen_package(2, requires=None))
        index.add(generator.gen_package(
            3, requires=generator.gen_relation("package10")
        ))
        unresolved = set(generator.gen_relation("package3"))
        resolved = RepositoryManager._get_minimal_subset(
            index, None, unresolved
        )
        self.assertItemsEqual(
            ["package3"],
            (x.name for x in resolved)
        )
        self.assertItemsEqual(
            ["package10"],
            (x.name for x in unresolved)
        )

    def test_get_packages_as_is(self):
        driver = mock.MagicMock()
        driver.get_repository.side_effect = generator.gen_repository
        driver.get_packages.side_effect = generator.gen_package
        manager = RepositoryManager(TestDriverAdapter(driver), "x86_64")
        packages = manager.get_packages("file:///repo1")
        self.assertEqual(1, len(packages))
        pkg = packages.pop()
        self.assertEqual("package1", pkg.name)
        self.assertEqual("file:///repo1", pkg.repository.url)

    def test_get_packages_with_depends_resolving(self):
        driver = mock.MagicMock()
        driver.get_repository.side_effect = generator.gen_repository
        driver.get_packages.side_effect = [
            generator.gen_package(
                idx=6, requires=generator.gen_relation("package2")
            ),
            [
                generator.gen_package(idx=1, requires=None),
                generator.gen_package(
                    idx=2, requires=generator.gen_relation("package1")
                ),
                generator.gen_package(
                    idx=3, requires=generator.gen_relation("package1")
                ),
                generator.gen_package(idx=4, requires=None)
            ],
            generator.gen_package(idx=5, requires=None),
        ]
        manager = RepositoryManager(TestDriverAdapter(driver), "x86_64")
        packages = manager.get_packages(["file:///repo1", "file:///repo2"],
                                        "file:///repo3", ["package4"])

        self.assertEqual(3, len(packages))
        self.assertItemsEqual(
            ["package1", "package4", "package2"],
            (x.name for x in packages)
        )

    def test_clone_repositories_as_is(self):
        driver = mock.MagicMock()
        repo = generator.gen_repository()
        mirror = generator.gen_repository()
        packages = [
            generator.gen_package(1, repository=repo, requires=None),
            generator.gen_package(2, repository=repo, requires=None)
        ]
        driver.get_repository.side_effect = [
            repo
        ]
        driver.clone_repository.return_value = mirror
        driver.get_packages.return_value = packages
        driver.copy_package.side_effect = [0, 1]
        manager = RepositoryManager(TestDriverAdapter(driver), "x86_64")
        stats = manager.clone_repositories(
            ["file:///repo1"], "/mirror", keep_existing=True
        )
        self.assertEqual(2, stats.total)
        self.assertEqual(1, stats.copied)
        for pkg in packages:
            driver.copy_package.assert_any_call(mirror, pkg, True)

    def test_copy_minimal_subset_from_repository(self):
        driver = mock.MagicMock()
        repo1 = generator.gen_repository(name="repo1")
        repo2 = generator.gen_repository(name="repo2")
        repo3 = generator.gen_repository(name="repo3")
        mirror1 = generator.gen_repository(name="mirror1")
        mirror2 = generator.gen_repository(name="mirror2")
        packages = [
            generator.gen_package(
                idx=6, requires=generator.gen_relation("package2")
            ),
            [
                generator.gen_package(
                    idx=1, requires=None, repository=repo1
                ),
                generator.gen_package(
                    idx=1, requires=None, version=2, repository=repo1
                ),
                generator.gen_package(
                    idx=2,
                    requires=generator.gen_relation("package1"),
                    repository=repo1
                ),
                generator.gen_package(
                    idx=3, requires=None, repository=repo1
                ),
                generator.gen_package(
                    idx=4,
                    requires=generator.gen_relation("package1"),
                    repository=repo1,
                    mandatory=True,
                )
            ],
            generator.gen_package(
                idx=1, requires=None, version=4, repository=repo2
            )
        ]
        driver.get_repository.side_effect = [repo3, repo1, repo2]
        driver.get_packages.side_effect = packages
        driver.clone_repository.side_effect = [mirror1, mirror2]
        driver.copy_package.side_effect = [0, 1, 2, 0, 4]
        manager = RepositoryManager(TestDriverAdapter(driver), "x86_64")
        stats = manager.clone_repositories(
            ["file:///repo1", "file:///repo2"], "/mirror",
            ["file:///repo3"],
            keep_existing=True
        )
        self.assertEqual(5, stats.total)
        self.assertEqual(3, stats.copied)
        driver.copy_package.assert_any_call(mirror2, packages[2], True)
        driver.copy_package.assert_any_call(mirror1, packages[1][0], True)
        driver.copy_package.assert_any_call(mirror1, packages[1][1], True)
        driver.copy_package.assert_any_call(mirror1, packages[1][2], True)
        driver.copy_package.assert_any_call(mirror1, packages[1][4], True)
        self.assertEqual(5, driver.copy_package.call_count)

    def test_warning_if_unresolved(self):
        driver = mock.MagicMock()
        driver.get_repository.side_effect = generator.gen_repository
        driver.get_packages.side_effect = generator.gen_package
        manager = RepositoryManager(TestDriverAdapter(driver), "x86_64")
        with warnings.catch_warnings(record=True) as log:
            manager.get_packages("file:///repo1", bootstrap=["package10"])
        self.assertIsInstance(log[0].message, UnresolvedWarning)
        self.assertIn("package10", log[0].message.message)
