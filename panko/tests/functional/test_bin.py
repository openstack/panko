# Copyright 2012 eNovance <licensing@enovance.com>
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

import os
import subprocess

from oslo_utils import fileutils
import six

from panko.tests import base


class BinTestCase(base.BaseTestCase):
    def setUp(self):
        super(BinTestCase, self).setUp()
        content = ("[database]\n"
                   "connection=log://localhost\n")
        if six.PY3:
            content = content.encode('utf-8')
        self.tempfile = fileutils.write_to_tempfile(content=content,
                                                    prefix='panko',
                                                    suffix='.conf')

    def tearDown(self):
        super(BinTestCase, self).tearDown()
        os.remove(self.tempfile)

    def test_dbsync_run(self):
        subp = subprocess.Popen(['panko-dbsync',
                                 "--config-file=%s" % self.tempfile])
        self.assertEqual(0, subp.wait())

    def test_run_expirer_ttl_disabled(self):
        subp = subprocess.Popen(['panko-expirer',
                                 '-d',
                                 "--config-file=%s" % self.tempfile],
                                stdout=subprocess.PIPE)
        out, __ = subp.communicate()
        self.assertEqual(0, subp.poll())
        self.assertIn(b"Nothing to clean, database event "
                      b"time to live is disabled", out)

    def _test_run_expirer_ttl_enabled(self, ttl_name, data_name):
        content = ("[database]\n"
                   "%s=1\n"
                   "connection=log://localhost\n" % ttl_name)
        if six.PY3:
            content = content.encode('utf-8')
        self.tempfile = fileutils.write_to_tempfile(content=content,
                                                    prefix='panko',
                                                    suffix='.conf')
        subp = subprocess.Popen(['panko-expirer',
                                 '-d',
                                 "--config-file=%s" % self.tempfile],
                                stdout=subprocess.PIPE)
        out, __ = subp.communicate()
        self.assertEqual(0, subp.poll())
        msg = "Dropping %s data with TTL 1" % data_name
        if six.PY3:
            msg = msg.encode('utf-8')
        self.assertIn(msg, out)

    def test_run_expirer_ttl_enabled(self):
        self._test_run_expirer_ttl_enabled('event_time_to_live', 'event')
