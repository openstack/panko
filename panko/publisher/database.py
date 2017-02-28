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

from panko import service
from panko import storage


class DatabasePublisher(object):
    """Publisher class for recording event data into database.

    The publisher class which records each event into a database configured
    in Ceilometer configuration file.

    To enable this publisher, the following section needs to be present in
    panko.conf file

    [database]
    connection = mysql+pymysql://panko:password@127.0.0.1/panko?charset=utf8

    Then, panko:// should be added to Ceilometer's event_pipeline.yaml
    """

    def __init__(self, parsed_url):
        conf = service.prepare_service([], share=True)
        self.conn = storage.get_connection_from_config(conf)

    def publish_events(self, events):
        if not isinstance(events, list):
            events = [events]
        self.conn.record_events(events)
