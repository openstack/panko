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
"""Tests for ceilometer/storage/impl_mongodb.py

.. note::
  In order to run the tests against another MongoDB server set the
  environment variable CEILOMETER_TEST_MONGODB_URL to point to a MongoDB
  server before running the tests.

"""

from ceilometer.event.storage import impl_mongodb
from ceilometer.tests import base as test_base
from ceilometer.tests import db as tests_db


@tests_db.run_with('mongodb')
class IndexTest(tests_db.TestBase):

    def _test_ttl_index_absent(self, conn, coll_name, ttl_opt):
        # create a fake index and check it is deleted
        coll = getattr(conn.db, coll_name)
        index_name = '%s_ttl' % coll_name
        self.CONF.set_override(ttl_opt, -1, group='database')
        conn.upgrade()
        self.assertNotIn(index_name, coll.index_information())

        self.CONF.set_override(ttl_opt, 456789, group='database')
        conn.upgrade()
        self.assertEqual(456789,
                         coll.index_information()
                         [index_name]['expireAfterSeconds'])

    def test_event_ttl_index_absent(self):
        self._test_ttl_index_absent(self.event_conn, 'event',
                                    'event_time_to_live')

    def _test_ttl_index_present(self, conn, coll_name, ttl_opt):
        coll = getattr(conn.db, coll_name)
        self.CONF.set_override(ttl_opt, 456789, group='database')
        conn.upgrade()
        index_name = '%s_ttl' % coll_name
        self.assertEqual(456789,
                         coll.index_information()
                         [index_name]['expireAfterSeconds'])

        self.CONF.set_override(ttl_opt, -1, group='database')
        conn.upgrade()
        self.assertNotIn(index_name, coll.index_information())

    def test_event_ttl_index_present(self):
        self._test_ttl_index_present(self.event_conn, 'event',
                                     'event_time_to_live')


class CapabilitiesTest(test_base.BaseTestCase):
    # Check the returned capabilities list, which is specific to each DB
    # driver

    def test_event_capabilities(self):
        expected_capabilities = {
            'events': {'query': {'simple': True}},
        }
        actual_capabilities = impl_mongodb.Connection.get_capabilities()
        self.assertEqual(expected_capabilities, actual_capabilities)
