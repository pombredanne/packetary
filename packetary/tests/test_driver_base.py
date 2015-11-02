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


#class TestDriverBase(base.TestCase):

    # def assign_packages(self, repository, packages, keep_existing=True):
    #     # """Assigns set of packages to the repository.
    #     #
    #     # :param repository: the target repository
    #     # :param packages: the set of packages
    #     # :param keep_existing:
    #     # """
    #     #
    #     # if not isinstance(packages, set):
    #     #     packages = set(packages)
    #     #
    #     # if keep_existing:
    #     #     consume_exist = packages.add
    #     # else:
    #     #     def consume_exist(p):
    #     #         if p not in packages:
    #     #             filepath = os.path.join(repository.url, p.filename)
    #     #             self.logger.info("remove package - %s.", filepath)
    #     #             os.remove(filepath)
    #     #
    #     # self.get_packages(repository, consume_exist)
    #     # self.rebuild_repository(repository, packages)
    #
    # def copy_packages(self, repository, packages, keep_existing, observer):
    #     # """Copies packages to repository.
    #     #
    #     # :param repository: the target repository
    #     # :param packages: the set of packages
    #     # :param keep_existing: see assign_packages for more details
    #     # :param observer: the package copying process observer
    #     # """
    #     # with self.context.async_section() as section:
    #     #     for package in packages:
    #     #         section.execute(
    #     #             self._copy_package, repository, package, observer
    #     #         )
    #     # self.assign_packages(repository, packages, keep_existing)
    #
    # def load_repositories(self, urls, arch, consumer):
    #     """Loads the repository objects from url.
    #
    #     :param urls: the list of repository urls.
    #     :param arch: the target architecture
    #     :param consumer: the callback to consume objects
    #     """
    #     for parsed_url in self.parse_urls(urls):
    #         self.get_repository(parsed_url, arch, consumer)
    #
    # def load_packages(self, repositories, consumer):
    #     """Loads packages from repository.
    #
    #     :param repositories: the repository object
    #     :param consumer: the callback to consume objects
    #     """
    #     for r in repositories:
    #         self.get_packages(r, consumer)
    #
    # def clone_repositories(self, repositories, destination,
    #                        source=False, locale=False):
    #     """Creates copy of repositories.
    #
    #     :param source: If True, the source packages will be copied too.
    #     :param locale: If True, the localisation will be copied too.
    #     :return: The the copy of repositories in same order.
    #     """
    #     result = []
    #     with self.context.async_section(0) as section:
    #         for r in repositories:
    #             result.append(section.execute(
    #                 self.clone_repository, r, destination,
    #                 source=source, locale=locale
    #             ))
    #     return [x.wait() for x in result]
