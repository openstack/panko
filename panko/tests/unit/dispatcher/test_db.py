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

import mock
from oslo_utils import uuidutils
from oslotest import base

from panko.dispatcher import database
from panko import service
from panko.storage import models


class TestDispatcherDB(base.BaseTestCase):

    def setUp(self):
        super(TestDispatcherDB, self).setUp()
        self.CONF = service.prepare_service([], [])
        self.CONF.set_override('connection', 'sqlite://', group='database')
        with mock.patch('panko.service.prepare_service') as f:
            f.return_value = self.CONF
            self.dispatcher = database.DatabaseDispatcher(None)

    def test_conn(self):
        event = models.Event(uuidutils.generate_uuid(), 'test',
                             datetime.datetime(2012, 7, 2, 13, 53, 40),
                             [], {}).serialize()
        with mock.patch.object(self.dispatcher.conn,
                               'record_events') as record_events:
            self.dispatcher.record_events(event)
        self.assertEqual(1, len(record_events.call_args_list[0][0][0]))
