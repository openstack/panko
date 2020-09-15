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

from oslo_log import log

from panko.storage import base

LOG = log.getLogger(__name__)


class Connection(base.Connection):
    """Log event data."""

    @staticmethod
    def clear_expired_data(ttl, max_count):
        """Clear expired data from the backend storage system.

        Clearing occurs according to the time-to-live.

        :param ttl: Number of seconds to keep records for.
        :param max_count: Number of records to delete.
        """
        LOG.info("Dropping %d events data with TTL %d", max_count, ttl)
