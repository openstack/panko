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
"""Test ACL."""

import datetime
import os

from keystonemiddleware import fixture as ksm_fixture
from oslo_utils import fileutils
from oslo_utils import uuidutils
import six
import webtest

from panko.api import app
from panko.storage import models
from panko.tests.functional.api import v2

VALID_TOKEN = uuidutils.generate_uuid(dashed=False)
VALID_TOKEN2 = uuidutils.generate_uuid(dashed=False)


class TestAPIACL(v2.FunctionalTest):

    def setUp(self):
        super(TestAPIACL, self).setUp()
        self.auth_token_fixture = self.useFixture(
            ksm_fixture.AuthTokenFixture())
        self.auth_token_fixture.add_token_data(
            token_id=VALID_TOKEN,
            # FIXME(morganfainberg): The project-id should be a proper uuid
            project_id='123i2910',
            role_list=['admin'],
            user_name='user_id2',
            user_id='user_id2',
            is_v2=True
        )
        self.auth_token_fixture.add_token_data(
            token_id=VALID_TOKEN2,
            # FIXME(morganfainberg): The project-id should be a proper uuid
            project_id='project-good',
            role_list=['Member'],
            user_name='user_id1',
            user_id='user_id1',
            is_v2=True)

    def get_json(self, path, expect_errors=False, headers=None,
                 q=None, **params):
        return super(TestAPIACL, self).get_json(path,
                                                expect_errors=expect_errors,
                                                headers=headers,
                                                q=q or [],
                                                **params)

    @staticmethod
    def _make_app(conf):
        return webtest.TestApp(app.load_app(conf, appname='panko+keystone'))


class TestAPIEventACL(TestAPIACL):

    PATH = '/events'

    def test_non_admin_get_event_types(self):
        data = self.get_json('/event_types', expect_errors=True,
                             headers={"X-Roles": "Member",
                                      "X-Auth-Token": VALID_TOKEN2,
                                      "X-Project-Id": "project-good"})
        self.assertEqual(401, data.status_int)


class TestBaseApiEventRBAC(v2.FunctionalTest):

    PATH = '/events'

    def setUp(self):
        super(TestBaseApiEventRBAC, self).setUp()
        traits = [models.Trait('project_id', 1, 'project-good'),
                  models.Trait('user_id', 1, 'user-good')]
        self.message_id = uuidutils.generate_uuid()
        ev = models.Event(self.message_id, 'event_type',
                          datetime.datetime.now(), traits, {})
        self.conn.record_events([ev])

    def test_get_events_without_project(self):
        headers_no_proj = {"X-Roles": "admin", "X-User-Id": "user-good"}
        resp = self.get_json(self.PATH, expect_errors=True,
                             headers=headers_no_proj, status=403)
        self.assertEqual(403, resp.status_int)

    def test_get_events_without_user(self):
        headers_no_user = {"X-Roles": "admin", "X-Project-Id": "project-good"}
        resp = self.get_json(self.PATH, expect_errors=True,
                             headers=headers_no_user, status=403)
        self.assertEqual(403, resp.status_int)

    def test_get_events_without_scope(self):
        headers_no_user_proj = {"X-Roles": "admin"}
        resp = self.get_json(self.PATH,
                             expect_errors=True,
                             headers=headers_no_user_proj,
                             status=403)
        self.assertEqual(403, resp.status_int)

    def test_get_events(self):
        headers = {"X-Roles": "Member", "X-User-Id": "user-good",
                   "X-Project-Id": "project-good"}
        self.get_json(self.PATH, headers=headers, status=200)

    def test_get_event(self):
        headers = {"X-Roles": "Member", "X-User-Id": "user-good",
                   "X-Project-Id": "project-good"}
        self.get_json(self.PATH + "/" + self.message_id, headers=headers,
                      status=200)


class TestApiEventAdminRBAC(TestBaseApiEventRBAC):

    def _make_app(self, conf):
        content = ('{"context_is_admin": "role:admin",'
                   '"telemetry:events:index": "rule:context_is_admin",'
                   '"telemetry:events:show": "rule:context_is_admin"}')
        if six.PY3:
            content = content.encode('utf-8')
        self.tempfile = fileutils.write_to_tempfile(content=content,
                                                    prefix='policy',
                                                    suffix='.json')

        conf.set_override("policy_file", self.tempfile, group='oslo_policy')
        return webtest.TestApp(app.load_app(conf, appname='panko+noauth'))

    def tearDown(self):
        os.remove(self.tempfile)
        super(TestApiEventAdminRBAC, self).tearDown()

    def test_get_events(self):
        headers_rbac = {"X-Roles": "admin", "X-User-Id": "user-good",
                        "X-Project-Id": "project-good"}
        self.get_json(self.PATH, headers=headers_rbac, status=200)

    def test_get_events_bad(self):
        headers_rbac = {"X-Roles": "Member", "X-User-Id": "user-good",
                        "X-Project-Id": "project-good"}
        self.get_json(self.PATH, headers=headers_rbac, status=403)

    def test_get_event(self):
        headers = {"X-Roles": "admin", "X-User-Id": "user-good",
                   "X-Project-Id": "project-good"}
        self.get_json(self.PATH + "/" + self.message_id, headers=headers,
                      status=200)

    def test_get_event_bad(self):
        headers = {"X-Roles": "Member", "X-User-Id": "user-good",
                   "X-Project-Id": "project-good"}
        self.get_json(self.PATH + "/" + self.message_id, headers=headers,
                      status=403)
