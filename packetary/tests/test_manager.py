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

from packetary.manager import Index
from packetary.manager import RepositoryManager
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

    def test_get_packages_without_depends(self):
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
        driver.get_repository.side_effect = generator.gen_repository
        driver.get_packages.side_effect = [
            generator.gen_package(1, requires=None),
            generator.gen_package(2, requires=None)
        ]
        driver.copy_package.side_effect = [0, 1]
        manager = RepositoryManager(TestDriverAdapter(driver), "x86_64")
        stats = manager.clone_repositories(["file:///repo1"], "/mirror", keep_existing=True)
        self.assertEqual(2, stats.total)
        self.assertEqual(1, stats.copied)
        driver.copy_packages.assert_any_call()



        #
        # count = api.createmirror(
        #     self.context,
        #     "test", "x86_64",
        #     "target",
        #     "file:///origin",
        #     "file:///debs",
        #     ["requires-1",
        #      "package-0"],
        #     True
        # )
        # repo_class.assert_called_once_with(
        #     self.context, "test", "x86_64"
        # )
        # self.assertEqual(2, count)

#  repos, packages = self._load_repositories_with_packages(
#             origin, debs, bootstrap
#         )
#         mirros = dict(six.moves.zip(
#             repos,
#             self.driver.clone_repositories(
#                 repos, os.path.abspath(destination)
#             )
#         ))
#
#         package_groups = dict((x, set()) for x in repos)
#         for pkg in packages:
#             package_groups[pkg.repository].add(pkg)
#
#         if keep_existing:
#             def consume_exist(p):
#                 package_groups[p.repository].add(p)
#
#         else:
#             def consume_exist(p):
#                 if p not in package_groups[p.repository]:
#                     filepath = os.path.join(repo.url, packages.filename)
#                     logger.info("remove package - %s.", filepath)
#                     os.remove(repo.url + packages.filename)
#
#         self.driver.load_packages(
#             six.itervalues(mirros),
#             consume_exist
#         )
#
#         stat = [0, 0]
#         for repo, packages in six.iteritems(package_groups):
#             logger.info("update repository: %s", repo.name)
#             self.driver.copy_packages(mirros[repo], packages, stat)
#         return stat

   #         packages = self.packages
   #      os.stat.side_effect = [
   #          mock.MagicMock(st_size=packages[0].size),
   #          mock.MagicMock(st_size=packages[1].size + 1),
   #          mock.MagicMock(st_size=packages[2].size - 1),
   #          OSError(2, "error")
   #      ]
   #
   #      self.repo.copy_packages(packages, "target", True)
   #      index_writer = self.repo.driver.create_index(".")
   #      self.assertEqual(
   #          len(packages), index_writer.add.call_count
   #      )
   #      index_writer.commit.assert_called_once_with(True)
   #
   #      retrieve = self.repo.context.connections.get().__enter__().retrieve
   #      call_args = retrieve.call_args_list
   #      self.assertEqual(3, retrieve.call_count)
   #      packages[1].props['size'] = 0
   #      packages[2].props['size'] -= 1
   #      packages[3].props['size'] = 0
   #
   #      for i in six.moves.range(3):
   #          self.assertItemsEqual(
   #              [
   #                  self.repo.driver.get_path(".", packages[i + 1]),
   #                  self.repo.driver.get_path("target", packages[i + 1]),
   #                  packages[i + 1].size,
   #              ],
   #              call_args[i][0]
   #          )


