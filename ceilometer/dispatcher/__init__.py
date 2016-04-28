#
# Copyright 2013 IBM
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import abc

from oslo_config import cfg
import six


STORAGE_OPTS = [
    cfg.IntOpt('max_retries',
               default=10,
               deprecated_group='database',
               help='Maximum number of connection retries during startup. '
                    'Set to -1 to specify an infinite retry count.'),
    cfg.IntOpt('retry_interval',
               default=10,
               deprecated_group='database',
               help='Interval (in seconds) between retries of connection.'),
]
cfg.CONF.register_opts(STORAGE_OPTS, group='storage')


@six.add_metaclass(abc.ABCMeta)
class EventDispatcherBase(object):
    def __init__(self, conf):
        self.conf = conf

    @abc.abstractmethod
    def record_events(self, events):
        """Record events."""
