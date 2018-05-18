#
# Copyright 2013 Intel Corp.
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
"""Base classes for DB backend implementation test"""

import datetime
import operator

import mock
from oslo_utils import timeutils

from panko import storage
from panko.storage import models
from panko.tests import db as tests_db


class EventTestBase(tests_db.TestBase):
    """Separate test base class.

    We don't want to inherit all the Meter stuff.
    """

    def setUp(self):
        super(EventTestBase, self).setUp()
        self.prepare_data()

    def prepare_data(self):
        self.models = []
        base = 0
        self.start = datetime.datetime(2013, 12, 31, 5, 0)
        now = self.start
        for event_type in ['Foo', 'Bar', 'Zoo', 'Foo', 'Bar', 'Zoo']:
            trait_models = [models.Trait(name, dtype, value)
                            for name, dtype, value in [
                                ('trait_A', models.Trait.TEXT_TYPE,
                                    "my_%s_text" % event_type),
                                ('trait_B', models.Trait.INT_TYPE,
                                    base + 1),
                                ('trait_C', models.Trait.FLOAT_TYPE,
                                    float(base) + 0.123456),
                                ('trait_D', models.Trait.DATETIME_TYPE,
                                    now)]]
            self.models.append(
                models.Event("id_%s_%d" % (event_type, base),
                             event_type, now, trait_models,
                             {'status': {'nested': 'started'}}))
            base += 100
            now = now + datetime.timedelta(hours=1)
        self.end = now

        self.conn.record_events(self.models)


@tests_db.run_with('sqlite', 'mysql', 'pgsql')
class EventTTLTest(EventTestBase):

    @mock.patch.object(timeutils, 'utcnow')
    def test_clear_expired_data(self, mock_utcnow):
        mock_utcnow.return_value = datetime.datetime(2013, 12, 31, 10, 0)
        self.conn.clear_expired_data(3600)

        events = list(self.conn.get_events(storage.EventFilter()))
        self.assertEqual(2, len(events))
        event_types = list(self.conn.get_event_types())
        self.assertEqual(['Bar', 'Zoo'], event_types)
        for event_type in event_types:
            trait_types = list(self.conn.get_trait_types(event_type))
            self.assertEqual(4, len(trait_types))
            traits = list(self.conn.get_traits(event_type))
            self.assertEqual(4, len(traits))


@tests_db.run_with('sqlite', 'mysql', 'pgsql', 'mongodb')
class EventTest(EventTestBase):
    def test_duplicate_message_id(self):
        now = datetime.datetime.utcnow()
        m = [models.Event("1", "Foo", now, None, {}),
             models.Event("1", "Zoo", now, [], {})]
        with mock.patch('%s.LOG' %
                        self.conn.record_events.__module__) as log:
            self.conn.record_events(m)
            self.assertEqual(1, log.debug.call_count)

    def test_bad_event(self):
        now = datetime.datetime.utcnow()
        broken_event = models.Event("1", "Foo", now, None, {})
        del(broken_event.__dict__['raw'])
        m = [broken_event, broken_event]
        with mock.patch('%s.LOG' %
                        self.conn.record_events.__module__) as log:
            self.assertRaises(AttributeError, self.conn.record_events, m)
            # ensure that record_events does not break on first error but
            # delays exception and tries to record each event.
            self.assertEqual(2, log.exception.call_count)


class BigIntegerTest(EventTestBase):
    def test_trait_bigint(self):
        big = 99999999999999
        new_events = [models.Event(
            "id_testid", "MessageIDTest", self.start,
            [models.Trait('int', models.Trait.INT_TYPE, big)], {})]
        self.conn.record_events(new_events)


class GetEventTest(EventTestBase):

    def test_generated_is_datetime(self):
        event_filter = storage.EventFilter(self.start, self.end)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(6, len(events))
        for i, event in enumerate(events):
            self.assertIsInstance(event.generated, datetime.datetime)
            self.assertEqual(event.generated,
                             self.models[i].generated)
            model_traits = self.models[i].traits
            for j, trait in enumerate(event.traits):
                if trait.dtype == models.Trait.DATETIME_TYPE:
                    self.assertIsInstance(trait.value, datetime.datetime)
                    self.assertEqual(trait.value, model_traits[j].value)

    def test_simple_get(self):
        event_filter = storage.EventFilter(self.start, self.end)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(6, len(events))
        start_time = None
        for i, type in enumerate(['Foo', 'Bar', 'Zoo']):
            self.assertEqual(type, events[i].event_type)
            self.assertEqual(4, len(events[i].traits))
            # Ensure sorted results ...
            if start_time is not None:
                # Python 2.6 has no assertLess :(
                self.assertTrue(start_time < events[i].generated)
            start_time = events[i].generated

    def test_simple_get_event_type(self):
        expected_trait_values = {
            'id_Bar_100': {
                'trait_A': 'my_Bar_text',
                'trait_B': 101,
                'trait_C': 100.123456,
                'trait_D': self.start + datetime.timedelta(hours=1)
            },
            'id_Bar_400': {
                'trait_A': 'my_Bar_text',
                'trait_B': 401,
                'trait_C': 400.123456,
                'trait_D': self.start + datetime.timedelta(hours=4)
            }
        }

        event_filter = storage.EventFilter(self.start, self.end, "Bar")
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(2, len(events))
        self.assertEqual("Bar", events[0].event_type)
        self.assertEqual("Bar", events[1].event_type)
        self.assertEqual(4, len(events[0].traits))
        self.assertEqual(4, len(events[1].traits))
        for event in events:
            trait_values = expected_trait_values.get(event.message_id,
                                                     None)
            if not trait_values:
                self.fail("Unexpected event ID returned:" % event.message_id)

            for trait in event.traits:
                expected_val = trait_values.get(trait.name)
                if not expected_val:
                    self.fail("Unexpected trait type: %s" % trait.dtype)
                self.assertEqual(expected_val, trait.value)

    def test_get_event_trait_filter(self):
        trait_filters = [{'key': 'trait_B', 'integer': 101}]
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(1, len(events))
        self.assertEqual("Bar", events[0].event_type)
        self.assertEqual(4, len(events[0].traits))

    def test_get_event_trait_filter_op_string(self):
        trait_filters = [{'key': 'trait_A', 'string': 'my_Foo_text',
                          'op': 'eq'}]
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(2, len(events))
        self.assertEqual("Foo", events[0].event_type)
        self.assertEqual(4, len(events[0].traits))
        trait_filters[0].update({'key': 'trait_A', 'op': 'lt'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(2, len(events))
        self.assertEqual("Bar", events[0].event_type)
        trait_filters[0].update({'key': 'trait_A', 'op': 'le'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(4, len(events))
        self.assertEqual("Bar", events[1].event_type)
        trait_filters[0].update({'key': 'trait_A', 'op': 'ne'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(4, len(events))
        self.assertEqual("Zoo", events[3].event_type)
        trait_filters[0].update({'key': 'trait_A', 'op': 'gt'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(2, len(events))
        self.assertEqual("Zoo", events[0].event_type)
        trait_filters[0].update({'key': 'trait_A', 'op': 'ge'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(4, len(events))
        self.assertEqual("Foo", events[2].event_type)

    def test_get_event_trait_filter_op_integer(self):
        trait_filters = [{'key': 'trait_B', 'integer': 101, 'op': 'eq'}]
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(1, len(events))
        self.assertEqual("Bar", events[0].event_type)
        self.assertEqual(4, len(events[0].traits))
        trait_filters[0].update({'key': 'trait_B', 'op': 'lt'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(1, len(events))
        self.assertEqual("Foo", events[0].event_type)
        trait_filters[0].update({'key': 'trait_B', 'op': 'le'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(2, len(events))
        self.assertEqual("Bar", events[1].event_type)
        trait_filters[0].update({'key': 'trait_B', 'op': 'ne'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(5, len(events))
        self.assertEqual("Zoo", events[4].event_type)
        trait_filters[0].update({'key': 'trait_B', 'op': 'gt'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(4, len(events))
        self.assertEqual("Zoo", events[0].event_type)
        trait_filters[0].update({'key': 'trait_B', 'op': 'ge'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(5, len(events))
        self.assertEqual("Foo", events[2].event_type)

    def test_get_event_trait_filter_op_float(self):
        trait_filters = [{'key': 'trait_C', 'float': 300.123456, 'op': 'eq'}]
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(1, len(events))
        self.assertEqual("Foo", events[0].event_type)
        self.assertEqual(4, len(events[0].traits))
        trait_filters[0].update({'key': 'trait_C', 'op': 'lt'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(3, len(events))
        self.assertEqual("Zoo", events[2].event_type)
        trait_filters[0].update({'key': 'trait_C', 'op': 'le'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(4, len(events))
        self.assertEqual("Bar", events[1].event_type)
        trait_filters[0].update({'key': 'trait_C', 'op': 'ne'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(5, len(events))
        self.assertEqual("Zoo", events[2].event_type)
        trait_filters[0].update({'key': 'trait_C', 'op': 'gt'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(2, len(events))
        self.assertEqual("Bar", events[0].event_type)
        trait_filters[0].update({'key': 'trait_C', 'op': 'ge'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(3, len(events))
        self.assertEqual("Zoo", events[2].event_type)

    def test_get_event_trait_filter_op_datetime(self):
        trait_filters = [{'key': 'trait_D',
                          'datetime': self.start + datetime.timedelta(hours=2),
                          'op': 'eq'}]
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(1, len(events))
        self.assertEqual("Zoo", events[0].event_type)
        self.assertEqual(4, len(events[0].traits))
        trait_filters[0].update({'key': 'trait_D', 'op': 'lt'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(2, len(events))
        trait_filters[0].update({'key': 'trait_D', 'op': 'le'})
        self.assertEqual("Bar", events[1].event_type)
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(3, len(events))
        self.assertEqual("Bar", events[1].event_type)
        trait_filters[0].update({'key': 'trait_D', 'op': 'ne'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(5, len(events))
        self.assertEqual("Foo", events[2].event_type)
        trait_filters[0].update({'key': 'trait_D', 'op': 'gt'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(3, len(events))
        self.assertEqual("Zoo", events[2].event_type)
        trait_filters[0].update({'key': 'trait_D', 'op': 'ge'})
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(4, len(events))
        self.assertEqual("Bar", events[2].event_type)

    def test_get_event_multiple_trait_filter(self):
        trait_filters = [{'key': 'trait_B', 'integer': 1},
                         {'key': 'trait_C', 'float': 0.123456},
                         {'key': 'trait_A', 'string': 'my_Foo_text'}]
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(1, len(events))
        self.assertEqual("Foo", events[0].event_type)
        self.assertEqual(4, len(events[0].traits))

    def test_get_event_multiple_trait_filter_expect_none(self):
        trait_filters = [{'key': 'trait_B', 'integer': 1},
                         {'key': 'trait_A', 'string': 'my_Zoo_text'}]
        event_filter = storage.EventFilter(self.start, self.end,
                                           traits_filter=trait_filters)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(0, len(events))

    def test_get_event_types(self):
        event_types = [e for e in
                       self.conn.get_event_types()]

        self.assertEqual(3, len(event_types))
        self.assertIn("Bar", event_types)
        self.assertIn("Foo", event_types)
        self.assertIn("Zoo", event_types)

    def test_get_trait_types(self):
        trait_types = [tt for tt in
                       self.conn.get_trait_types("Foo")]
        self.assertEqual(4, len(trait_types))
        trait_type_names = map(lambda x: x['name'], trait_types)
        self.assertIn("trait_A", trait_type_names)
        self.assertIn("trait_B", trait_type_names)
        self.assertIn("trait_C", trait_type_names)
        self.assertIn("trait_D", trait_type_names)

    def test_get_trait_types_unknown_event(self):
        trait_types = [tt for tt in
                       self.conn.get_trait_types("Moo")]
        self.assertEqual(0, len(trait_types))

    def test_get_traits(self):
        traits = self.conn.get_traits("Bar")
        # format results in a way that makes them easier to work with
        trait_dict = {}
        for trait in traits:
            trait_dict[trait.name] = trait.dtype

        self.assertIn("trait_A", trait_dict)
        self.assertEqual(models.Trait.TEXT_TYPE, trait_dict["trait_A"])
        self.assertIn("trait_B", trait_dict)
        self.assertEqual(models.Trait.INT_TYPE, trait_dict["trait_B"])
        self.assertIn("trait_C", trait_dict)
        self.assertEqual(models.Trait.FLOAT_TYPE, trait_dict["trait_C"])
        self.assertIn("trait_D", trait_dict)
        self.assertEqual(models.Trait.DATETIME_TYPE,
                         trait_dict["trait_D"])

    def test_get_all_traits(self):
        traits = self.conn.get_traits("Foo")
        traits = sorted([t for t in traits], key=operator.attrgetter('dtype'))
        self.assertEqual(8, len(traits))
        trait = traits[0]
        self.assertEqual("trait_A", trait.name)
        self.assertEqual(models.Trait.TEXT_TYPE, trait.dtype)

    def test_simple_get_event_no_traits(self):
        new_events = [models.Event("id_notraits", "NoTraits",
                      self.start, [], {})]
        self.conn.record_events(new_events)
        event_filter = storage.EventFilter(
            self.start, self.end, "NoTraits")
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(1, len(events))
        self.assertEqual("id_notraits", events[0].message_id)
        self.assertEqual("NoTraits", events[0].event_type)
        self.assertEqual(0, len(events[0].traits))

    def test_simple_get_no_filters(self):
        event_filter = storage.EventFilter(None, None, None)
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(6, len(events))

    def test_get_by_message_id(self):
        new_events = [models.Event("id_testid", "MessageIDTest",
                                   self.start, [], {})]

        self.conn.record_events(new_events)
        event_filter = storage.EventFilter(message_id="id_testid")
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertEqual(1, len(events))
        event = events[0]
        self.assertEqual("id_testid", event.message_id)

    def test_simple_get_raw(self):
        event_filter = storage.EventFilter()
        events = [event for event in self.conn.get_events(event_filter)]
        self.assertTrue(events)
        self.assertEqual({'status': {'nested': 'started'}}, events[0].raw)

    def test_trait_type_enforced_on_none(self):
        new_events = [models.Event(
            "id_testid", "MessageIDTest", self.start,
            [models.Trait('text', models.Trait.TEXT_TYPE, ''),
             models.Trait('int', models.Trait.INT_TYPE, 0),
             models.Trait('float', models.Trait.FLOAT_TYPE, 0.0)],
            {})]
        self.conn.record_events(new_events)
        event_filter = storage.EventFilter(message_id="id_testid")
        events = [event for event in self.conn.get_events(event_filter)]
        options = [(models.Trait.TEXT_TYPE, ''),
                   (models.Trait.INT_TYPE, 0.0),
                   (models.Trait.FLOAT_TYPE, 0.0)]
        for trait in events[0].traits:
            options.remove((trait.dtype, trait.value))
