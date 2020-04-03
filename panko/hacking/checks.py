# Copyright (c) 2016 OpenStack Foundation
# All Rights Reserved.
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

"""
Guidelines for writing new hacking checks

 - Use only for Panko specific tests. OpenStack general tests
   should be submitted to the common 'hacking' module.
 - Pick numbers in the range X3xx. Find the current test with
   the highest allocated number and then pick the next value.
 - Keep the test method code in the source file ordered based
   on the C3xx value.
 - List the new rule in the top level HACKING.rst file

"""

from hacking import core


@core.flake8ext
def no_log_warn(logical_line):
    """Disallow 'LOG.warn('

    https://bugs.launchpad.net/tempest/+bug/1508442

    C301
    """
    if logical_line.startswith('LOG.warn('):
        yield(0, 'C301 Use LOG.warning() rather than LOG.warn()')


@core.flake8ext
def no_os_popen(logical_line):
    """Disallow 'os.popen('

    Deprecated library function os.popen() Replace it using subprocess
    https://bugs.launchpad.net/tempest/+bug/1529836

    C302
    """

    if 'os.popen(' in logical_line:
        yield(0, 'C302 Deprecated library function os.popen(). '
                 'Replace it using subprocess module. ')
