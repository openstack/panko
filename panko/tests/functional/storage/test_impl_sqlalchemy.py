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
"""Tests for panko/storage/impl_sqlalchemy.py

.. note::
  In order to run the tests against real SQL server set the environment
  variable PANKO_TEST_SQL_URL to point to a SQL server before running
  the tests.

"""

import datetime

from six.moves import reprlib

from panko.storage import impl_sqlalchemy as impl_sqla_event
from panko.storage import models
from panko.storage.sqlalchemy import models as sql_models
from panko.tests import base as test_base
from panko.tests import db as tests_db


@tests_db.run_with('sqlite', 'mysql', 'pgsql')
class PankoBaseTest(tests_db.TestBase):

    def test_panko_base(self):
        base = sql_models.PankoBase()
        base['key'] = 'value'
        self.assertEqual('value', base['key'])


@tests_db.run_with('sqlite', 'mysql', 'pgsql')
class EventTypeTest(tests_db.TestBase):
    # EventType is a construct specific to sqlalchemy
    # Not applicable to other drivers.

    def setUp(self):
        super(EventTypeTest, self).setUp()
        self.session = self.conn._engine_facade.get_session()
        self.session.begin()

    def test_event_type_exists(self):
        et1 = self.conn._get_or_create_event_type("foo", self.session)
        self.assertTrue(et1.id >= 0)
        et2 = self.conn._get_or_create_event_type("foo", self.session)
        self.assertEqual(et2.id, et1.id)
        self.assertEqual(et2.desc, et1.desc)

    def test_event_type_unique(self):
        et1 = self.conn._get_or_create_event_type("foo", self.session)
        self.assertTrue(et1.id >= 0)
        et2 = self.conn._get_or_create_event_type("blah", self.session)
        self.assertNotEqual(et1.id, et2.id)
        self.assertNotEqual(et1.desc, et2.desc)
        # Test the method __repr__ returns a string
        self.assertTrue(reprlib.repr(et2))

    def tearDown(self):
        self.session.rollback()
        self.session.close()
        super(EventTypeTest, self).tearDown()


@tests_db.run_with('sqlite', 'mysql', 'pgsql')
class EventTest(tests_db.TestBase):
    def _verify_data(self, trait, trait_table):
        now = datetime.datetime.utcnow()
        ev = models.Event('1', 'name', now, [trait], {})
        self.conn.record_events([ev])
        session = self.conn._engine_facade.get_session()
        t_tables = [sql_models.TraitText, sql_models.TraitFloat,
                    sql_models.TraitInt, sql_models.TraitDatetime]
        for table in t_tables:
            if table == trait_table:
                self.assertEqual(1, session.query(table).count())
            else:
                self.assertEqual(0, session.query(table).count())

    def test_string_traits(self):
        model = models.Trait("Foo", models.Trait.TEXT_TYPE, "my_text")
        self._verify_data(model, sql_models.TraitText)

    def test_int_traits(self):
        model = models.Trait("Foo", models.Trait.INT_TYPE, 100)
        self._verify_data(model, sql_models.TraitInt)

    def test_float_traits(self):
        model = models.Trait("Foo", models.Trait.FLOAT_TYPE, 123.456)
        self._verify_data(model, sql_models.TraitFloat)

    def test_datetime_traits(self):
        now = datetime.datetime.utcnow()
        model = models.Trait("Foo", models.Trait.DATETIME_TYPE, now)
        self._verify_data(model, sql_models.TraitDatetime)

    def test_event_repr(self):
        ev = sql_models.Event('msg_id', None, False, {})
        ev.id = 100
        self.assertTrue(reprlib.repr(ev))


class CapabilitiesTest(test_base.BaseTestCase):
    # Check the returned capabilities list, which is specific to each DB
    # driver

    def test_capabilities(self):
        expected_capabilities = {
            'events': {'query': {'simple': True}},
        }
        actual_capabilities = impl_sqla_event.Connection.get_capabilities()
        self.assertEqual(expected_capabilities, actual_capabilities)
