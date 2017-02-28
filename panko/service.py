# Copyright 2012-2014 eNovance <licensing@enovance.com>
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

import sys

from oslo_config import cfg
from oslo_db import options as db_options
import oslo_i18n
from oslo_log import log
from oslo_reports import guru_meditation_report as gmr

from panko.conf import defaults
from panko import opts
from panko import version


def prepare_service(argv=None, config_files=None, share=False):
    conf = cfg.ConfigOpts()
    for group, options in opts.list_opts():
        conf.register_opts(list(options),
                           group=None if group == "DEFAULT" else group)
    db_options.set_defaults(conf)
    if not share:
        defaults.set_cors_middleware_defaults()
        oslo_i18n.enable_lazy()
        log.register_options(conf)

    if argv is None:
        argv = sys.argv
    conf(argv[1:], project='panko', validate_default_values=True,
         version=version.version_info.version_string(),
         default_config_files=config_files)

    if not share:
        log.setup(conf, 'panko')
    # NOTE(liusheng): guru cannot run with service under apache daemon, so when
    # panko-api running with mod_wsgi, the argv is [], we don't start
    # guru.
    if argv:
        gmr.TextGuruMeditation.setup_autorun(version)
    return conf
