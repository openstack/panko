# Copyright 2014 eNovance
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
from oslo_config import cfg

import panko.dispatcher
import panko.storage
import panko.utils


def list_opts():
    return [
        ('DEFAULT',
         [
             # FIXME(jd) Move to [api]
             cfg.StrOpt('api_paste_config',
                        default="api_paste.ini",
                        help="Configuration file for WSGI definition of API."),
         ]),
        ('api',
         [
             cfg.IntOpt('default_api_return_limit',
                        min=1,
                        default=100,
                        help='Default maximum number of '
                        'items returned by API request.'),
         ]),
        ('database', panko.storage.OPTS),
        ('storage', panko.dispatcher.STORAGE_OPTS),
    ]
