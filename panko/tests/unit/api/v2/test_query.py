# Copyright 2013 OpenStack Foundation.
# All Rights Reserved.
# Copyright 2013 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Test the methods related to query."""
import datetime

import fixtures
import mock
from oslotest import base
import wsme

from panko.api.controllers.v2 import base as v2_base
from panko.api.controllers.v2 import events


class TestQuery(base.BaseTestCase):
    def setUp(self):
        super(TestQuery, self).setUp()
        self.useFixture(fixtures.MonkeyPatch(
            'pecan.response', mock.MagicMock()))
        self.useFixture(fixtures.MockPatch('panko.api.controllers.v2.events'
                                           '._build_rbac_query_filters',
                                           return_value={'t_filter': [],
                                                         'admin_proj': None}))

    def test_get_value_as_type_with_integer(self):
        query = v2_base.Query(field='metadata.size',
                              op='eq',
                              value='123',
                              type='integer')
        expected = 123
        self.assertEqual(expected, query._get_value_as_type())

    def test_get_value_as_type_with_float(self):
        query = v2_base.Query(field='metadata.size',
                              op='eq',
                              value='123.456',
                              type='float')
        expected = 123.456
        self.assertEqual(expected, query._get_value_as_type())

    def test_get_value_as_type_with_boolean(self):
        query = v2_base.Query(field='metadata.is_public',
                              op='eq',
                              value='True',
                              type='boolean')
        expected = True
        self.assertEqual(expected, query._get_value_as_type())

    def test_get_value_as_type_with_string(self):
        query = v2_base.Query(field='metadata.name',
                              op='eq',
                              value='linux',
                              type='string')
        expected = 'linux'
        self.assertEqual(expected, query._get_value_as_type())

    def test_get_value_as_type_with_datetime(self):
        query = v2_base.Query(field='metadata.date',
                              op='eq',
                              value='2014-01-01T05:00:00',
                              type='datetime')
        self.assertIsInstance(query._get_value_as_type(), datetime.datetime)
        self.assertIsNone(query._get_value_as_type().tzinfo)

    def test_get_value_as_type_with_integer_without_type(self):
        query = v2_base.Query(field='metadata.size',
                              op='eq',
                              value='123')
        expected = 123
        self.assertEqual(expected, query._get_value_as_type())

    def test_get_value_as_type_with_float_without_type(self):
        query = v2_base.Query(field='metadata.size',
                              op='eq',
                              value='123.456')
        expected = 123.456
        self.assertEqual(expected, query._get_value_as_type())

    def test_get_value_as_type_with_boolean_without_type(self):
        query = v2_base.Query(field='metadata.is_public',
                              op='eq',
                              value='True')
        expected = True
        self.assertEqual(expected, query._get_value_as_type())

    def test_get_value_as_type_with_string_without_type(self):
        query = v2_base.Query(field='metadata.name',
                              op='eq',
                              value='linux')
        expected = 'linux'
        self.assertEqual(expected, query._get_value_as_type())

    def test_get_value_as_type_with_bad_type(self):
        query = v2_base.Query(field='metadata.size',
                              op='eq',
                              value='123.456',
                              type='blob')
        self.assertRaises(wsme.exc.ClientSideError, query._get_value_as_type)

    def test_get_value_as_type_with_bad_value(self):
        query = v2_base.Query(field='metadata.size',
                              op='eq',
                              value='fake',
                              type='integer')
        self.assertRaises(wsme.exc.ClientSideError, query._get_value_as_type)

    def test_get_value_as_type_integer_expression_without_type(self):
        # bug 1221736
        query = v2_base.Query(field='should_be_a_string',
                              op='eq',
                              value='WWW-Layer-4a80714f')
        expected = 'WWW-Layer-4a80714f'
        self.assertEqual(expected, query._get_value_as_type())

    def test_get_value_as_type_boolean_expression_without_type(self):
        # bug 1221736
        query = v2_base.Query(field='should_be_a_string',
                              op='eq',
                              value='True or False')
        expected = 'True or False'
        self.assertEqual(expected, query._get_value_as_type())

    def test_get_value_as_type_with_syntax_error(self):
        # bug 1221736
        value = 'WWW-Layer-4a80714f-0232-4580-aa5e-81494d1a4147-uolhh25p5xxm'
        query = v2_base.Query(field='group_id',
                              op='eq',
                              value=value)
        expected = value
        self.assertEqual(expected, query._get_value_as_type())

    def test_get_value_as_type_with_syntax_error_colons(self):
        # bug 1221736
        value = 'Ref::StackId'
        query = v2_base.Query(field='field_name',
                              op='eq',
                              value=value)
        expected = value
        self.assertEqual(expected, query._get_value_as_type())

    def test_event_query_to_event_filter_with_bad_op(self):
        # bug 1511592
        query = v2_base.Query(field='event_type',
                              op='ne',
                              value='compute.instance.create.end',
                              type='string')
        self.assertRaises(v2_base.ClientSideError,
                          events._event_query_to_event_filter, [query])
