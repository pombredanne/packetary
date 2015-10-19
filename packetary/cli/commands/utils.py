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


import six


def read_lines_from_file(filename):
    """Reads lines from file."""
    with open(filename, 'r') as f:
        return [
            x.strip() for x in f.readlines()
            if not x.startswith("#")
        ]


def get_object_attrs(obj, fields):
    """Gets object attributes as list."""
    return [getattr(obj, f) for f in fields]


def get_display_value(v):
    """Gets v in displayable format."""
    if not v:
        return six.u("-")

    if isinstance(v, list):
        return six.u(", ").join(six.text_type(x) for x in v)
    return six.text_type(v)


def make_display_attr_getter(fields):
    """Gets object attributes in displayable format."""
    return lambda x: [
        get_display_value(v) for v in get_object_attrs(x, fields)
    ]
