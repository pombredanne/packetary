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


import abc
import six


@six.add_metaclass(abc.ABCMeta)
class Repository(object):
    """Abstraction to manage repositories."""

    @abc.abstractmethod
    def load(self, url, consumer):
        """Load the packages from url."""

    @abc.abstractmethod
    def clone(self, provider, destination):
        """Saves the repository the specified path."""

    @abc.abstractmethod
    def rebuild_index(self, provider, destination):
        """Rebuilds index."""