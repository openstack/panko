#
# Copyright 2013 IBM Corp
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
import datetime
import uuid

import mock
from oslo_config import fixture as fixture_config
from oslotest import base

from ceilometer.dispatcher import database
from ceilometer.event.storage import models as event_models


class TestDispatcherDB(base.BaseTestCase):

    def setUp(self):
        super(TestDispatcherDB, self).setUp()
        self.CONF = self.useFixture(fixture_config.Config()).conf
        self.CONF.set_override('connection', 'sqlite://', group='database')
        self.dispatcher = database.DatabaseDispatcher(self.CONF)
        self.ctx = None

    def test_event_conn(self):
        event = event_models.Event(uuid.uuid4(), 'test',
                                   datetime.datetime(2012, 7, 2, 13, 53, 40),
                                   [], {}).serialize()
        with mock.patch.object(self.dispatcher.event_conn,
                               'record_events') as record_events:
            self.dispatcher.record_events(event)
        self.assertEqual(1, len(record_events.call_args_list[0][0][0]))
