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
import six


def filter_in_set(choices, iterable, key=None, attr=None):
    """Filters by next(data)[field] in choices."""

    choices = set(choices)
    if key is not None and attr is not None:
        raise ValueError("'key' and 'attr' cannot be specified"
                         "simultaneously.")

    if key is not None:
        def function(x):
            return x[key] in choices
    else:
        def function(x):
            return getattr(x, attr) in choices

    return six.moves.filter(function, iterable)


def find_by_attributes(iterable, **attributes):
    """Finds element by attributes."""
    for i in iterable:
        for k, v in six.iteritems(attributes):
            if i.get(k) != v:
                break
        else:
            return i


def lists_merge(main, patch, key):
    """Merges the list of dicts with same keys."""

    main = copy.copy(main)
    main_idx = dict(
        (x[key], i) for i, x in enumerate(main)
    )

    patch_idx = dict(
        (x[key], i) for i, x in enumerate(patch)
    )

    for k in sorted(patch_idx):
        if k in main_idx:
            main[main_idx[k]].update(patch[patch_idx[k]])
        else:
            main.append(patch[patch_idx[k]])

    return main
