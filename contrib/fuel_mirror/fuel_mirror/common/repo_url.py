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


def get_url_parser(kind):
    """Gets the instance of RepoUrlParser."""
    return {
        "deb": DebUrlParser,
        "yum": YumUrlParser
    }[kind]()


@six.add_metaclass(abc.ABCMeta)
class RepoUrlParser(object):
    @abc.abstractmethod
    def join(self, baseurl, repo_uri):
        """Gets the url for repo."""

    @abc.abstractmethod
    def get_name(self, first_name, repo_uri):
        """Gets the name for repo."""

    @abc.abstractmethod
    def get_repo_config(self, name, url):
        """Gets the config for repo in fuel compatible format."""

    def format_url(self, baseurl, uri, **kwargs):
        """Get the url with replaced variable holders."""
        return self.join(baseurl, uri).format(**kwargs)

    def get_urls(self, baseurl, uris, **kwargs):
        """Get the urls from uris."""
        return [
            self.format_url(baseurl, x, **kwargs) for x in uris
        ]


class DebUrlParser(RepoUrlParser):
    def get_name(self, first_name, uri):
        suite = uri.split(" ", 1)[0].rsplit("-", 1)
        if len(suite) > 1:
            return "-".join((first_name, suite[-1]))
        return first_name

    def join(self, baseurl, uri):
        baseurl = baseurl.rstrip()
        return " ".join((baseurl, uri))

    def get_repo_config(self, name, url):
        baseurl, suite, section = url.split(" ", 2)
        return {
            "name": name,
            "section": section,
            "suite": suite,
            "type": "deb",
            "uri": baseurl,
        }


class YumUrlParser(RepoUrlParser):
    def get_name(self, first_name, uri):
        return "-".join((first_name, uri))

    def join(self, baseurl, uri):
        baseurl = baseurl.rstrip("/")
        return "/".join((baseurl, uri))

    def get_repo_config(self, name, url):
        return {
            "name": name,
            "type": "rpm",
            "uri": url,
        }
