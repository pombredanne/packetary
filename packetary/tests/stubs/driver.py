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

import copy


class TestDriverAdapter(object):
    def __init__(self, driver):
        self.driver = driver
        self.idx = 1

    def __getattr__(self, item):
        return getattr(self.driver, item)

    @staticmethod
    def parse_urls(urls):
        return iter(urls)

    def get_repository(self, url, arch, consumer):
        self._consume(
            self.driver.get_repository(url=url, architecture=arch),
            consumer
        )

    def get_packages(self, repository, consumer):
        self._consume(
            self.driver.get_packages(idx=self.idx, repository=repository),
            consumer
        )
        self.idx += 1

    def copy_packages(self, repository, packages, keep_existing, observer):
        for pkg in packages:
            observer(self.driver.copy_package(repository, pkg, keep_existing))

    def load_repositories(self, urls, arch, consumer):
        for parsed_url in self.parse_urls(urls):
            self.get_repository(parsed_url, arch, consumer)

    def load_packages(self, repositories, consumer):
        for r in repositories:
            self.get_packages(r, consumer)

    def clone_repositories(self, repositories, destination,
                           source=False, locale=False):
        result = []
        for r in repositories:
            result.append(self.driver.clone_repository(
                r, destination, source, locale
            ))
        return result

    @staticmethod
    def _consume(data, consumer):
        if isinstance(data, list):
            for d in data:
                consumer(d)
        else:
            consumer(data)
