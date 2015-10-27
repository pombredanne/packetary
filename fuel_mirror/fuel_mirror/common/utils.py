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

import six


def filter_contains(choices, field, iterable):
    """Filters by next(data)[field] in choices."""

    choices = set(choices)

    def function(x):
        return x[field] in choices

    return six.moves.filter(function, iterable)


def find_by_attributes(iterable, **attributes):
    """Finds element by attributes."""
    for i in iterable:
        for k, v in six.iteritems(attributes):
            if i.get(k) != v:
                break
        else:
            return i

def list_merge(src, list_b):
    """merges two lists """"
    if not isinstance(list_b, list):
        return deepcopy(list_b)

    to_merge = list_a + list_b
    primary_repos = sorted(filter(
        lambda x:
        x['name'].startswith(DISTROS.ubuntu)
        or x['name'].startswith(UBUNTU_CODENAME),
        to_merge))

    result = OrderedDict()
    for repo in primary_repos:
        result[repo['name']] = None

    for repo in to_merge:
        name = repo['name']
        if repo.get('delete') is True:
            result.pop(name, None)
        else:
            result[name] = repo

    return result.values()
