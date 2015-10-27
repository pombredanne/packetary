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

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class RepoUrlParser(object):
    @abc.abstractmethod
    def join(self, baseurl, repo_uri):
        """Gets the url for repo."""

    @abc.abstractmethod
    def get_name(self, first_name, repo_uri):
        """Gets the name for repo."""

    def get_urls(self, baseurl, repos_uri):
        return [
            self.join(baseurl, x) for x in repos_uri
        ]


class DebUrlParser(RepoUrlParser):
    def get_name(self, first_name, uri):
        last_name = uri.split(" ", 1)[0].rsplit("-", 1)[-1]
        if last_name:
            return "-".join((first_name, last_name))
        return first_name

    def join(self, baseurl, uri):
        baseurl = baseurl.rstrip()
        return " ".join((baseurl, uri))


class YumUrlParser(RepoUrlParser):
    def get_name(self, first_name, uri):
        return "-".join((first_name, uri))

    def join(self, baseurl, uri):
        baseurl = baseurl.rstrip("/")
        return "/".join((baseurl, uri))


def get_url_parser(kind):
    return {
        "deb": DebUrlParser,
        "yum": YumUrlParser
    }[kind]()
