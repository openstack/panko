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

import os

from oslo_config import cfg
from oslo_log import log
from oslo_utils import uuidutils
from paste import deploy
import pecan

from panko.api import hooks
from panko.api import middleware
from panko import service

LOG = log.getLogger(__name__)


def setup_app(pecan_config=None, conf=None):
    if conf is None:
        raise RuntimeError("No configuration passed")
    # FIXME: Replace DBHook with a hooks.TransactionHook
    app_hooks = [hooks.ConfigHook(conf),
                 hooks.DBHook(conf),
                 hooks.TranslationHook()]

    pecan_config = pecan_config or {
        "app": {
            'root': 'panko.api.controllers.root.RootController',
            'modules': ['panko.api'],
        }
    }

    pecan.configuration.set_config(dict(pecan_config), overwrite=True)

    app = pecan.make_app(
        pecan_config['app']['root'],
        hooks=app_hooks,
        wrap_app=middleware.ParsableErrorMiddleware,
        guess_content_type_from_ext=False
    )

    return app


# NOTE(sileht): pastedeploy uses ConfigParser to handle
# global_conf, since python 3 ConfigParser doesn't
# allow to store object as config value, only strings are
# permit, so to be able to pass an object created before paste load
# the app, we store them into a global var. But the each loaded app
# store it's configuration in unique key to be concurrency safe.
global APPCONFIGS
APPCONFIGS = {}


def load_app(conf):
    global APPCONFIGS

    # Build the WSGI app
    cfg_file = None
    cfg_path = conf.api_paste_config
    if not os.path.isabs(cfg_path):
        cfg_file = conf.find_file(cfg_path)
    elif os.path.exists(cfg_path):
        cfg_file = cfg_path

    if not cfg_file:
        raise cfg.ConfigFilesNotFoundError([conf.api_paste_config])

    configkey = uuidutils.generate_uuid()
    APPCONFIGS[configkey] = conf

    LOG.info("Full WSGI config used: %s" % cfg_file)
    return deploy.loadapp("config:" + cfg_file,
                          global_conf={'configkey': configkey})


def build_wsgi_app(argv=None):
    return load_app(service.prepare_service(argv=argv))


def app_factory(global_config, **local_conf):
    global APPCONFIGS
    conf = APPCONFIGS.get(global_config.get('configkey'))
    return setup_app(conf=conf)
