#
# Copyright 2012 New Dream Network, LLC (DreamHost)
# Copyright 2013 IBM Corp.
# Copyright 2013 eNovance <licensing@enovance.com>
# Copyright Ericsson AB 2013. All rights reserved
# Copyright 2014 Hewlett-Packard Company
# Copyright 2015 Huawei Technologies Co., Ltd.
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

import functools

import pecan

from panko.api.controllers.v2 import base
from panko.api import rbac


def get_auth_project(on_behalf_of=None):
    auth_project = rbac.get_limited_to_project(pecan.request.headers)
    created_by = pecan.request.headers.get('X-Project-Id')
    is_admin = auth_project is None

    if is_admin and on_behalf_of != created_by:
        auth_project = on_behalf_of
    return auth_project


# TODO(fabiog): this decorator should disappear and have a more unified
# way of controlling access and scope. Before messing with this, though
# I feel this file should be re-factored in smaller chunks one for each
# controller (e.g. meters and so on ...). Right now its size is
# overwhelming.
def requires_admin(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        usr_limit, proj_limit = rbac.get_limited_to(pecan.request.headers)
        # If User and Project are None, you have full access.
        if usr_limit and proj_limit:
            # since this decorator get's called out of wsme context
            # raising exception results internal error so call abort
            # for handling the error
            ex = base.ProjectNotAuthorized(proj_limit)
            pecan.core.abort(status_code=ex.code, detail=ex.msg)
        return func(*args, **kwargs)

    return wrapped


def requires_context(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        req_usr = pecan.request.headers.get('X-User-Id')
        proj_usr = pecan.request.headers.get('X-Project-Id')
        if ((not req_usr) or (not proj_usr)):
            pecan.core.abort(status_code=403,
                             detail='RBAC Authorization Failed')
        return func(*args, **kwargs)

    return wrapped
