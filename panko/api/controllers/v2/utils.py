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
import wsme

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


def set_pagination_options(sort, limit, marker, api_model):
    """Sets the options for pagination specifying query options

    Arguments:
    sort -- List of sorting criteria. Each sorting option has to format
            <sort key>:<sort direction>

            Valid sort keys: message_id, generated
                    (SUPPORT_SORT_KEYS in panko/event/storage/models.py)
            Valid sort directions: asc (ascending), desc (descending)
                    (SUPPORT_DIRS in panko/event/storage/models.py)
                    This defaults to asc if unspecified
                    (DEFAULT_DIR in panko/event/storage/models.py)

            impl_sqlalchemy.py:
            (see _get_pagination_query)
            If sort list is empty, this defaults to
            ['generated:asc', 'message_id:asc']
                    (DEFAULT_SORT in panko/event/storage/models.py)

    limit -- Integer specifying maximum number of values to return

            If unspecified, this defaults to
            pecan.request.cfg.api.default_api_return_limit
    marker -- If specified, assumed to be an integer and assumed to be the
              message id of the last object on the previous page of the results
    api_model -- Specifies the class implementing the api model to use for
                 this pagination. The class is expected to provide the
                 following members:

                 SUPPORT_DIRS
                 SUPPORT_SORT_KEYS
                 DEFAULT_DIR
                 DEFAULT_SORT
                 PRIMARY_KEY
    """
    if limit and limit <= 0:
        raise wsme.exc.InvalidInput('limit', limit,
                                    'the limit should be a positive integer.')
    if not limit:
        limit = pecan.request.cfg.api.default_api_return_limit

    sorts = list()
    for s in sort or []:
        sort_key, __, sort_dir = s.partition(':')
        if sort_key not in api_model.SUPPORT_SORT_KEYS:
            raise wsme.exc.InvalidInput(
                'sort', s, "the sort parameter should be a pair of sort "
                "key and sort dir combined with ':', or only"
                " sort key specified and sort dir will be default "
                "'%s', the supported sort keys are: %s" %
                (str(api_model.DEFAULT_DIR),
                 str(api_model.SUPPORT_SORT_KEYS)))
        if sort_dir and sort_dir not in api_model.SUPPORT_DIRS:
            raise wsme.exc.InvalidInput(
                'sort direction', s,
                "the sort parameter should be a pair of sort "
                "key and sort dir combined with ':', or only"
                " sort key specified and sort dir will be default "
                "'%s', the supported sort directions are: %s" %
                (str(api_model.DEFAULT_DIR),
                 str(api_model.SUPPORT_DIRS)))
        sorts.append((sort_key, sort_dir or api_model.DEFAULT_DIR))

    return {'limit': limit,
            'marker': marker,
            'sort': sorts}
