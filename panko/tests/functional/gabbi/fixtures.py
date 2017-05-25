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

from gabbi import fixture
from oslo_config import cfg
from oslo_policy import opts
from oslo_utils import fileutils
from oslo_utils import uuidutils
import six
from six.moves.urllib import parse as urlparse
import sqlalchemy_utils

from panko.api import app
from panko import service
from panko import storage
from panko.storage import models

# NOTE(chdent): Hack to restore semblance of global configuration to
# pass to the WSGI app used per test suite. LOAD_APP_KWARGS are the olso
# configuration, and the pecan application configuration of
# which the critical part is a reference to the current indexer.
LOAD_APP_KWARGS = None


def setup_app():
    global LOAD_APP_KWARGS
    return app.load_app(**LOAD_APP_KWARGS)


class ConfigFixture(fixture.GabbiFixture):
    """Establish the relevant configuration for a test run."""

    def start_fixture(self):
        """Set up config."""

        global LOAD_APP_KWARGS

        self.conf = None

        # Determine the database connection.
        db_url = os.environ.get('PIFPAF_URL', "sqlite://").replace(
            "mysql://", "mysql+pymysql://")
        if not db_url:
            raise case.SkipTest('No database connection configured')

        conf = self.conf = service.prepare_service([], [])
        opts.set_defaults(self.conf)

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
            os.path.abspath('etc/panko/api_paste.ini')
        )

        parsed_url = list(urlparse.urlparse(db_url))
        parsed_url[2] += '-%s' % uuidutils.generate_uuid(dashed=False)
        db_url = urlparse.urlunparse(parsed_url)

        conf.set_override('connection', db_url, group='database')

        if (parsed_url[0].startswith("mysql")
           or parsed_url[0].startswith("postgresql")):
            sqlalchemy_utils.create_database(conf.database.connection)

        self.conn = storage.get_connection_from_config(self.conf)
        self.conn.upgrade()

        LOAD_APP_KWARGS = {
            'conf': conf, 'appname': 'panko+noauth',
        }

    def stop_fixture(self):
        """Reset the config and remove data."""
        if self.conn:
            self.conn.clear()
        if self.conf:
            storage.get_connection_from_config(self.conf).clear()


class EventDataFixture(ConfigFixture):
    """Instantiate some sample event data for use in testing."""

    def start_fixture(self):
        """Create some events."""
        super(EventDataFixture, self).start_fixture()
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
