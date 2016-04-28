#
# Copyright 2015 Red Hat. All Rights Reserved.
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

"""Fixtures used during Gabbi-based test runs."""

import datetime
import os
from unittest import case
import uuid

from gabbi import fixture
from oslo_config import cfg
from oslo_config import fixture as fixture_config
from oslo_policy import opts
from oslo_utils import fileutils
import six
from six.moves.urllib import parse as urlparse

from ceilometer.event.storage import models
from ceilometer import storage

# TODO(chdent): For now only MongoDB is supported, because of easy
# database name handling and intentional focus on the API, not the
# data store.
ENGINES = ['mongodb']


class ConfigFixture(fixture.GabbiFixture):
    """Establish the relevant configuration for a test run."""

    def start_fixture(self):
        """Set up config."""

        self.conf = None

        # Determine the database connection.
        db_url = os.environ.get('PIFPAF_URL', "sqlite://").replace(
            "mysql://", "mysql+pymysql://")
        if not db_url:
            raise case.SkipTest('No database connection configured')

        engine = urlparse.urlparse(db_url).scheme
        if engine not in ENGINES:
            raise case.SkipTest('Database engine not supported')

        conf = fixture_config.Config().conf
        self.conf = conf
        self.conf([], project='ceilometer', validate_default_values=True)
        opts.set_defaults(self.conf)
        conf.import_group('api', 'ceilometer.api.controllers.v2.root')

        content = ('{"default": ""}')
        if six.PY3:
            content = content.encode('utf-8')
        self.tempfile = fileutils.write_to_tempfile(content=content,
                                                    prefix='policy',
                                                    suffix='.json')

        conf.set_override("policy_file", self.tempfile,
                          group='oslo_policy')
        conf.set_override(
            'api_paste_config',
            os.path.abspath(
                'ceilometer/tests/functional/gabbi/gabbi_paste.ini')
        )

        database_name = '%s-%s' % (db_url, str(uuid.uuid4()))
        conf.set_override('connection', database_name, group='database')
        conf.set_override('event_connection', '', group='database')

        conf.set_override('pecan_debug', True, group='api')

    def stop_fixture(self):
        """Reset the config and remove data."""
        if self.conf:
            storage.get_connection_from_config(self.conf).clear()
            self.conf.reset()


class EventDataFixture(fixture.GabbiFixture):
    """Instantiate some sample event data for use in testing."""

    def start_fixture(self):
        """Create some events."""
        conf = fixture_config.Config().conf
        self.conn = storage.get_connection_from_config(conf)
        events = []
        name_list = ['chocolate.chip', 'peanut.butter', 'sugar']
        for ix, name in enumerate(name_list):
            timestamp = datetime.datetime.utcnow()
            message_id = 'fea1b15a-1d47-4175-85a5-a4bb2c72924{}'.format(ix)
            traits = [models.Trait('type', 1, name),
                      models.Trait('ate', 2, ix)]
            event = models.Event(message_id,
                                 'cookies_{}'.format(name),
                                 timestamp,
                                 traits, {'nested': {'inside': 'value'}})
            events.append(event)
        self.conn.record_events(events)

    def stop_fixture(self):
        """Destroy the events."""
        self.conn.db.event.remove({'event_type': '/^cookies_/'})


class CORSConfigFixture(fixture.GabbiFixture):
    """Inject mock configuration for the CORS middleware."""

    def start_fixture(self):
        # Here we monkeypatch GroupAttr.__getattr__, necessary because the
        # paste.ini method of initializing this middleware creates its own
        # ConfigOpts instance, bypassing the regular config fixture.

        def _mock_getattr(instance, key):
            if key != 'allowed_origin':
                return self._original_call_method(instance, key)
            return "http://valid.example.com"

        self._original_call_method = cfg.ConfigOpts.GroupAttr.__getattr__
        cfg.ConfigOpts.GroupAttr.__getattr__ = _mock_getattr

    def stop_fixture(self):
        """Remove the monkeypatch."""
        cfg.ConfigOpts.GroupAttr.__getattr__ = self._original_call_method
