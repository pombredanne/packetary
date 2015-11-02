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

from cliff.command import Command as BaseCommand
from packetary.objects.statistics import CopyStatistics

from fuel_mirror.common.repo_url import get_url_parser
from fuel_mirror.common.utils import filter_in_set
from fuel_mirror.common.utils import find_by_attributes
from fuel_mirror.common.utils import lists_merge


logger = logging.getLogger(__package__)

_DEFAULT_ARCHITECTURE = "x86_64"


class CreateCommand(BaseCommand):
    def get_parser(self, prog_name):
        parser = super(CreateCommand, self).get_parser(prog_name)
        parser.add_argument(
            "-d", "--no-default",
            dest="set_default",
            action="store_false",
            default=True,
            help="Do not set as default repository."
        )
        parser.add_argument(
            "-a", "--no-apply",
            dest="apply",
            action="store_false",
            default=True,
            help="Do not apply for environments."
        )
        parser.add_argument(
            "-F", "--full",
            dest="partial",
            action="store_false",
            default=True,
            help="Do no analyze dependencies, create full mirror."
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
            "-B", "--base",
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
            help="Clones the repositories for CentOs."
        )
        parser.add_argument(
            "-e", "--env",
            dest="env", nargs="+",
            help="Fuel environment ID to update"
        )

        return parser

    def take_action(self, parsed_args):
        """See the Command.take_action.

        :return: the result of take_repo_action
        :rtype: object
        """
        repo_configs = dict()
        stats = self.copy_repositories(parsed_args, repo_configs)
        self.app.stdout.write("Packages processed: {0.copied}/{0.total}\n".format(stats))
        if parsed_args.apply:
            self.app.stdout.write("Updated clusters:\n")
            self.update_clusters(repo_configs, parsed_args.env)
        if parsed_args.set_default:
            self.app.stdout.write("Updated defaults:\n")
            self.update_default_repos(repo_configs)
        self.app.stdout.write("Operation has been completed successfully.\n")

    def copy_repositories(self, parsed_args, fuel_repos):
        """Copies repositories to local fs."""
        repo_url = self.app.config["http_base"]
        repo_folder = self.app.config["repo_folder"]
        total = CopyStatistics()
        for repo_config in self.filter_repositories(parsed_args):
            name = repo_config["name"]
            osname = repo_config["osname"]
            baseurl = repo_config["baseurl"]
            repo_type = repo_config["type"]
            repo_manager = self.app.repo_manager_accessor(
                repo_type, _DEFAULT_ARCHITECTURE
            )
            url_parser = get_url_parser(repo_config["type"])
            if osname != name:
                folder = name, osname
            else:
                folder = name,

            localurl = "/".join((repo_url, "mirror") + folder)
            destination = os.path.abspath(
                os.path.join(repo_folder, "mirror", *folder)
            )

            if parsed_args.partial and 'master' in repo_config:
                master = find_by_attributes(
                    self.app.sources,
                    name=repo_config["master"],
                    osname=osname
                )
                deps = url_parser.get_urls(
                    master["baseurl"],
                    master["repositories"],
                    **self.app.versions
                )
                requires = repo_config.get('bootstrap')
            else:
                deps = None
                requires = None

            os_repos = fuel_repos.setdefault(osname, [])
            repository_urls = []
            for repo in repo_config["repositories"]:
                repository_urls.append(
                    url_parser.format_url(baseurl, repo, **self.app.versions)
                )
                os_repos.append(
                    url_parser.get_repo_config(
                        url_parser.get_name(name, repo),
                        url_parser.format_url(
                            localurl, repo, **self.app.versions
                        )
                    )
                )

            total += repo_manager.clone_repositories(
                repository_urls,
                destination,
                deps,
                requires
            )
            # optimisation for further access
            repo_config["baseurl"] = "file://" + destination
        return total

    def filter_repositories(self, parsed_args):
        """Gets the list of repositories according to settings."""
        sources = self.app.sources

        if parsed_args.sources:
            sources_filter = set(parsed_args.sources)
            if "system" in sources_filter:
                sources_filter.remove("system")
                sources = (x for x in sources if x["name"] == x["osname"])
            if sources_filter:
                sources = filter_in_set(
                    parsed_args.sources, sources, key="name"
                )
        if parsed_args.releases:
            sources = filter_in_set(
                parsed_args.releases, sources, key="osname"
            )
        return sources

    def update_clusters(self, repositories, ids=None):
        """Applies repositories for existing clusters."""
        logger.info("Updating repositories...")
        clusters = self.app.fuel.Environment.get_all()
        if ids:
            clusters = filter_in_set(ids, clusters, attr="id")

        for cluster in clusters:
            release = self.app.fuel.Release.get_by_ids(
                [cluster.data["release_id"]]
            )[0]
            osname = release.data["operating_system"].lower()
            if osname not in repositories:
                logger.info(
                    'Cluster "%s" does not relevant repositories was updated.',
                    cluster.data["name"]
                )
                continue

            modified = self.update_repository_settings(
                cluster.get_settings_data(),
                repositories[osname]
            )
            if modified:
                logger.debug("Try to update cluster attributes: %s", modified)
                cluster.set_settings_data(modified)

    def update_default_repos(self, repositories):
        """Applies repositories for existing default settings."""

        for release in self.app.fuel.Release.get_all():
            osname = release.data['operating_system'].lower()
            if osname not in repositories:
                logger.info(
                    'Release "%s" does not relevant repositories was updated.',
                    release.data["name"]
                )
                continue

            if self.update_repository_settings(
                release.data["attributes_metadata"], repositories[osname]
            ):
                # TODO(need to add method for release object)
                release.connection.put_request(
                    release.instance_api_path.format(release.id),
                    release.data
                )

    @staticmethod
    def update_repository_settings(attributes, repositories):
        """Updates repository settings."""
        editable = attributes["editable"]
        if 'repo_setup' not in editable:
            logger.info('Attributes is read-only.')
            return

        repos_attr = editable["repo_setup"]["repos"]
        repos_attr['value'] = lists_merge(
            repos_attr['value'], repositories, "name"
        )
        return {"editable": {"repo_setup": {"repos": repos_attr}}}


def debug(argv=None):
    from fuel_mirror.app import debug

    debug("create", CreateCommand, argv)


if __name__ == "__main__":
    debug()
