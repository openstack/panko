#
# Copyright 2012 New Dream Network, LLC (DreamHost)
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
"""Tests for panko/storage/
"""

import mock
from oslotest import base
import six

from panko import service
from panko import storage
from panko.storage import impl_log
from panko.storage import impl_sqlalchemy


class EngineTest(base.BaseTestCase):
    def test_get_connection(self):
        engine = storage.get_connection('log://localhost', None)
        self.assertIsInstance(engine, impl_log.Connection)

    def test_get_connection_no_such_engine(self):
        try:
            storage.get_connection('no-such-engine://localhost', None)
        except RuntimeError as err:
            self.assertIn('no-such-engine', six.text_type(err))


class ConnectionRetryTest(base.BaseTestCase):
    def setUp(self):
        super(ConnectionRetryTest, self).setUp()
        self.CONF = service.prepare_service([], config_files=[])

    def test_retries(self):
        # stevedore gives warning log instead of any exception
        with mock.patch.object(storage, 'get_connection',
                               side_effect=Exception) as retries:
            try:
                self.CONF.set_override("retry_interval", 1,
                                       group="database")
                self.CONF.set_override("max_retries", 3,
                                       group="database")
                storage.get_connection_from_config(self.CONF)
            except Exception:
                self.assertEqual(3, retries.call_count)
            else:
                self.fail()


class ConnectionConfigTest(base.BaseTestCase):
    def setUp(self):
        super(ConnectionConfigTest, self).setUp()
        self.CONF = service.prepare_service([], config_files=[])

    def test_only_default_url(self):
        self.CONF.set_override("connection", "log://", group="database")
        conn = storage.get_connection_from_config(self.CONF)
        self.assertIsInstance(conn, impl_log.Connection)

    def test_two_urls(self):
        self.CONF.set_override("connection", "log://", group="database")
        self.CONF.set_override("event_connection", "sqlite://",
                               group="database")
        conn = storage.get_connection_from_config(self.CONF)
        self.assertIsInstance(conn, impl_log.Connection)

    def test_sqlalchemy_driver(self):
        self.CONF.set_override("connection", "sqlite+pysqlite://",
                               group="database")
        conn = storage.get_connection_from_config(self.CONF)
        self.assertIsInstance(conn, impl_sqlalchemy.Connection)
