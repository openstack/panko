#
# Copyright Ericsson AB 2013. All rights reserved
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
"""Common functions for MongoDB backend
"""

import weakref

from oslo_log import log
from oslo_utils import netutils
import pymongo
import pymongo.errors
import six
import tenacity

from panko.i18n import _

ERROR_INDEX_WITH_DIFFERENT_SPEC_ALREADY_EXISTS = 86

LOG = log.getLogger(__name__)

EVENT_TRAIT_TYPES = {'none': 0, 'string': 1, 'integer': 2, 'float': 3,
                     'datetime': 4}
OP_SIGN = {'lt': '$lt', 'le': '$lte', 'ne': '$ne', 'gt': '$gt', 'ge': '$gte'}

MINIMUM_COMPATIBLE_MONGODB_VERSION = [2, 4]
COMPLETE_AGGREGATE_COMPATIBLE_VERSION = [2, 6]


def make_timestamp_range(start, end,
                         start_timestamp_op=None, end_timestamp_op=None):

    """Create the query document to find timestamps within that range.

    This is done by given two possible datetimes and their operations.
    By default, using $gte for the lower bound and $lt for the upper bound.
    """
    ts_range = {}

    if start:
        if start_timestamp_op == 'gt':
            start_timestamp_op = '$gt'
        else:
            start_timestamp_op = '$gte'
        ts_range[start_timestamp_op] = start

    if end:
        if end_timestamp_op == 'le':
            end_timestamp_op = '$lte'
        else:
            end_timestamp_op = '$lt'
        ts_range[end_timestamp_op] = end
    return ts_range


def make_events_query_from_filter(event_filter):
    """Return start and stop row for filtering and a query.

    Query is based on the selected parameter.

    :param event_filter: storage.EventFilter object.
    """
    query = {}
    q_list = []
    ts_range = make_timestamp_range(event_filter.start_timestamp,
                                    event_filter.end_timestamp)
    if ts_range:
        q_list.append({'timestamp': ts_range})
    if event_filter.event_type:
        q_list.append({'event_type': event_filter.event_type})
    if event_filter.message_id:
        q_list.append({'_id': event_filter.message_id})

    if event_filter.traits_filter:
        for trait_filter in event_filter.traits_filter:
            op = trait_filter.pop('op', 'eq')
            dict_query = {}
            for k, v in six.iteritems(trait_filter):
                if v is not None:
                    # All parameters in EventFilter['traits'] are optional, so
                    # we need to check if they are in the query or no.
                    if k == 'key':
                        dict_query.setdefault('trait_name', v)
                    elif k in ['string', 'integer', 'datetime', 'float']:
                        dict_query.setdefault('trait_type',
                                              EVENT_TRAIT_TYPES[k])
                        dict_query.setdefault('trait_value',
                                              v if op == 'eq'
                                              else {OP_SIGN[op]: v})
            dict_query = {'$elemMatch': dict_query}
            q_list.append({'traits': dict_query})
    if event_filter.admin_proj:
        q_list.append({'$or': [
            {'traits': {'$not': {'$elemMatch': {'trait_name': 'project_id'}}}},
            {'traits': {
                '$elemMatch': {'trait_name': 'project_id',
                               'trait_value': event_filter.admin_proj}}}]})
    if q_list:
        query = {'$and': q_list}

    return query


class ConnectionPool(object):

    def __init__(self):
        self._pool = {}

    def connect(self, url, max_retries, retry_interval):
        connection_options = pymongo.uri_parser.parse_uri(url)
        del connection_options['database']
        del connection_options['username']
        del connection_options['password']
        del connection_options['collection']
        pool_key = tuple(connection_options)

        if pool_key in self._pool:
            client = self._pool.get(pool_key)()
            if client:
                return client
        splitted_url = netutils.urlsplit(url)
        log_data = {'db': splitted_url.scheme,
                    'nodelist': connection_options['nodelist']}
        LOG.info('Connecting to %(db)s on %(nodelist)s' % log_data)
        try:
            client = MongoProxy(pymongo.MongoClient(url),
                                max_retries, retry_interval)
        except pymongo.errors.ConnectionFailure as e:
            LOG.warning(_('Unable to connect to the database server: '
                        '%(errmsg)s.') % {'errmsg': e})
            raise
        self._pool[pool_key] = weakref.ref(client)
        return client


def _safe_mongo_call(max_retries, retry_interval):
    return tenacity.retry(
        retry=tenacity.retry_if_exception_type(
            pymongo.errors.AutoReconnect),
        wait=tenacity.wait_fixed(retry_interval),
        stop=(tenacity.stop_after_attempt(max_retries) if max_retries >= 0
              else tenacity.stop_never)
    )


MONGO_METHODS = set([typ for typ in dir(pymongo.collection.Collection)
                     if not typ.startswith('_')])
MONGO_METHODS.update(set([typ for typ in dir(pymongo.MongoClient)
                          if not typ.startswith('_')]))
MONGO_METHODS.update(set([typ for typ in dir(pymongo)
                          if not typ.startswith('_')]))


class MongoProxy(object):
    def __init__(self, conn, max_retries, retry_interval):
        self.conn = conn
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self._recreate_index = _safe_mongo_call(
            self.max_retries, self.retry_interval)(self._recreate_index)

    def __getitem__(self, item):
        """Create and return proxy around the method in the connection.

        :param item: name of the connection
        """
        return MongoProxy(self.conn[item])

    def find(self, *args, **kwargs):
        # We need this modifying method to return a CursorProxy object so that
        # we can handle the Cursor next function to catch the AutoReconnect
        # exception.
        return CursorProxy(self.conn.find(*args, **kwargs),
                           self.max_retries,
                           self.retry_interval)

    def create_index(self, keys, name=None, *args, **kwargs):
        try:
            self.conn.create_index(keys, name=name, *args, **kwargs)
        except pymongo.errors.OperationFailure as e:
            if e.code is ERROR_INDEX_WITH_DIFFERENT_SPEC_ALREADY_EXISTS:
                LOG.info("Index %s will be recreate." % name)
                self._recreate_index(keys, name, *args, **kwargs)

    def _recreate_index(self, keys, name, *args, **kwargs):
        self.conn.drop_index(name)
        self.conn.create_index(keys, name=name, *args, **kwargs)

    def __getattr__(self, item):
        """Wrap MongoDB connection.

        If item is the name of an executable method, for example find or
        insert, wrap this method in the MongoConn.
        Else wrap getting attribute with MongoProxy.
        """
        if item in ('name', 'database'):
            return getattr(self.conn, item)
        if item in MONGO_METHODS:
            return _safe_mongo_call(
                self.max_retries, self.retry_interval
            )(getattr(self.conn, item))
        return MongoProxy(getattr(self.conn, item),
                          self.max_retries, self.retry_interval)

    def __call__(self, *args, **kwargs):
        return self.conn(*args, **kwargs)


class CursorProxy(pymongo.cursor.Cursor):
    def __init__(self, cursor, max_retry, retry_interval):
        self.cursor = cursor
        self.next = _safe_mongo_call(max_retry, retry_interval)(self._next)

    def __getitem__(self, item):
        return self.cursor[item]

    def _next(self):
        """Wrap Cursor next method.

        This method will be executed before each Cursor next method call.
        """
        try:
            save_cursor = self.cursor.clone()
            return self.cursor.next()
        except pymongo.errors.AutoReconnect:
            self.cursor = save_cursor
            raise

    def __getattr__(self, item):
        return getattr(self.cursor, item)
