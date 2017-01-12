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
"""Tests for panko/storage/impl_mongodb.py

.. note::
  In order to run the tests against another MongoDB server set the
  environment variable PANKO_TEST_MONGODB_URL to point to a MongoDB
  server before running the tests.

"""

from panko.storage import impl_mongodb
from panko.tests import base as test_base
from panko.tests import db as tests_db


@tests_db.run_with('mongodb')
class IndexTest(tests_db.TestBase):

    def test_event_ttl_index_absent(self):
        # create a fake index and check it is deleted
        self.conn.clear_expired_data(-1)
        self.assertNotIn("event_ttl",
                         self.conn.db.event.index_information())

        self.conn.clear_expired_data(456789)
        self.assertEqual(456789,
                         self.conn.db.event.index_information()
                         ["event_ttl"]['expireAfterSeconds'])

    def test_event_ttl_index_present(self):
        self.conn.clear_expired_data(456789)
        self.assertEqual(456789,
                         self.conn.db.event.index_information()
                         ["event_ttl"]['expireAfterSeconds'])

        self.conn.clear_expired_data(-1)
        self.assertNotIn("event_ttl",
                         self.conn.db.event.index_information())


class CapabilitiesTest(test_base.BaseTestCase):
    # Check the returned capabilities list, which is specific to each DB
    # driver

    def test_capabilities(self):
        expected_capabilities = {
            'events': {'query': {'simple': True}},
        }
        actual_capabilities = impl_mongodb.Connection.get_capabilities()
        self.assertEqual(expected_capabilities, actual_capabilities)
