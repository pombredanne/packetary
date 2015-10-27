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

import logging
import os
import six

from cliff.command import Command
from fuelclient.objects import Environment
from fuelclient.objects import Release
from packetary import api

from fuel_mirror.common.utils import filter_contains
from fuel_mirror.common.utils import find_by_attributes
from fuel_mirror.common.urls import get_url_parser


logger = logging.getLogger(__package__)

_DEFAULT_ARCHITECTURE = "x86_64"


class CreateMirrorCommand(Command):
    def get_parser(self, prog_name):
        parser = super(Command, self).get_parser(prog_name)
        parser.add_argument(
            "-d", "--no-default",
            dest="set_default",
            action="store_false",
            default=True,
            help="Path to config file."
        )
        parser.add_argument(
            "-a", "--no-apply",
            dest="apply",
            action="store_false",
            default=True,
            help="Path to config file."
        )
        parser.add_argument(
            "-F", "--full",
            dest="partial",
            action="store_false",
            default=True,
            help="Path to config file."
        )

        repos_group = parser.add_argument_group()
        repos_group.add_argument(
            "-M", "--mos",
            dest="sources",
            action="append_const",
            const="mos",
            help="Clones the repositories of MOS."
        )
        repos_group.add_argument(
            "-S", "--system",
            dest="sources",
            action="append_const",
            const="system",
            help="Clones the repositories of system."
        )

        dist_group = parser.add_argument_group()
        dist_group.add_argument(
            "-U", "--ubuntu",
            dest="releases",
            action="append_const",
            const="ubuntu",
            help="Clones the repositories for Ubuntu."
        )
        dist_group.add_argument(
            "-C", "--centos",
            dest="releases",
            action="append_const",
            const="centos",
            help="Clones the repositories for Centos."
        )

        return parser

    def take_action(self, parsed_args):
        """See the Command.take_action.

        :return: the result of take_repo_action
        :rtype: object
        """
        local_urls = dict()
        count = self.copy_repositories(parsed_args, local_urls)
        self.app.stdout.write("Packages processed: {0}\n".format(count))
        if self.apply:
            self.app.stdout.write("Updated clusters:\n")
            self.update_clusters(local_urls)
        if self.set_default:
            self.app.stdout.write("Updated defaults:\n")
            self.set_cluster_default(local_urls)
        self.app.stdout.write("Operation has been completed successfully.\n")

    def copy_repositories(self, parsed_args, local_urls):
        """Copies repositories to local fs."""
        count = 0
        destination_base = self.app.config["destination"]
        localurl_base = self.app.config["localurl"]
        for repo_config in self.filter_repositories(parsed_args):
            name = repo_config["name"]
            osname = repo_config["osname"]
            url_parser = get_url_parser(repo_config["type"])
            localurl = "/".join((
                localurl_base, "mirror", name, osname
            ))
            destination = os.path.join(
                destination_base, "mirror", name, osname
            )

            if self.partial and 'master' in repo_config:
                master = find_by_attributes(
                    self.app.sources,
                    name=repo_config["master"],
                    osname=osname
                )
                deps = url_parser.get_urls(
                    master["baseurl"],
                    master["repositories"]
                )
                requires = master['requirements']
            else:
                deps = None
                requires = None

            origin_url = repo_config["baseurl"]
            urls = local_urls.setdefault(osname, dict())
            origin = list()
            for r in repo_config["repositories"]:
                origin.append(url_parser.join(origin_url, r))
                urls[url_parser.get_name(name, r)] = url_parser.join(localurl, r)

            count += api.createmirror(
                self.app.packetary_context,
                repo_config["type"],
                _DEFAULT_ARCHITECTURE,
                destination,
                self.get_urls(repo_config),
                deps,
                requires,
            )
        return count

    def filter_repositories(self, parsed_args):
        """Gets the list of repositories according to settings."""
        sources = self.app.sources

        if parsed_args.sources:
            sources = filter_contains(parsed_args.sources, "name", sources)
        if parsed_args.releases:
            sources = filter_contains(parsed_args.sources, "os", sources)
        return sources

    def update_clusters(self, repositories):
        """Updates a cluster with new settings."""
        logger.info("Updating repositories...")
        for cluster in Environment.get_all():
            release = Release.get_by_ids([cluster.data["release_id"]])[0]
            osname = release["operating_system"].lower()
            if osname not in repositories:
                logger.info(
                    'Cluster "%s" does not relevant repositories was updated.',
                    cluster.data["name"]
                )
                continue

            attributes = cluster.get_settings_data()["editable"]
            if 'repo_setup' not in attributes['editable']:
                logger.info(
                    'Cluster "%s" is read-only.',
                    cluster.data["name"]
                )
                continue

            repos_attr = attributes['editable']['repo_setup']['repos']
            repos_attr['value'] = self.repo_merge(
                repos_attr['value'], repositories[osname]
            )

        logger.debug("Try to update cluster "
                     "with next attributes {0}".format(attributes))

        self.client.update_cluster_attributes(cluster_id, attributes)

    def update_default_repos(self,
                             release_id,
                             settings=None):
        """Updates a cluster with new settings

        :param cluster_id:
        :param settings:
        """

        if settings is None:
            settings = {}

        attributes = self.client.get_release_attributes(release_id)
        if 'repo_setup' in attributes['attributes_metadata']['editable']:
            repos_attr = \
                attributes['attributes_metadata']['editable']['repo_setup'][
                    'repos']
            repos_attr['value'] = repo_merge(repos_attr['value'], settings)

        logger.debug("Try to update release "
                     "with next attributes {0}".format(attributes))
        self.client.update_release_attributes(release_id, attributes)
