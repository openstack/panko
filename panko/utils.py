# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Justin Santa Barbara

# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Utilities and helper functions."""

import calendar
import copy
import datetime
import decimal

from oslo_utils import timeutils
from oslo_utils import units


def decode_unicode(input):
    """Decode the unicode of the message, and encode it into utf-8."""
    if isinstance(input, dict):
        temp = {}
        # If the input data is a dict, create an equivalent dict with a
        # predictable insertion order to avoid inconsistencies in the
        # message signature computation for equivalent payloads modulo
        # ordering
        for key, value in sorted(input.items()):
            temp[decode_unicode(key)] = decode_unicode(value)
        return temp
    elif isinstance(input, (tuple, list)):
        # When doing a pair of JSON encode/decode operations to the tuple,
        # the tuple would become list. So we have to generate the value as
        # list here.
        return [decode_unicode(element) for element in input]
    elif isinstance(input, bytes):
        return input.decode('utf-8')
    else:
        return input


def recursive_keypairs(d, separator=':'):
    """Generator that produces sequence of keypairs for nested dictionaries."""
    for name, value in sorted(d.items()):
        if isinstance(value, dict):
            for subname, subvalue in recursive_keypairs(value, separator):
                yield ('%s%s%s' % (name, separator, subname), subvalue)
        elif isinstance(value, (tuple, list)):
            yield name, decode_unicode(value)
        else:
            yield name, value


def dt_to_decimal(utc):
    """Datetime to Decimal.

    Some databases don't store microseconds in datetime
    so we always store as Decimal unixtime.
    """
    if utc is None:
        return None

    decimal.getcontext().prec = 30
    return (decimal.Decimal(str(calendar.timegm(utc.utctimetuple()))) +
            (decimal.Decimal(str(utc.microsecond)) /
            decimal.Decimal("1000000.0")))


def decimal_to_dt(dec):
    """Return a datetime from Decimal unixtime format."""
    if dec is None:
        return None

    integer = int(dec)
    micro = (dec - decimal.Decimal(integer)) * decimal.Decimal(units.M)
    daittyme = datetime.datetime.utcfromtimestamp(integer)
    return daittyme.replace(microsecond=int(round(micro)))


def sanitize_timestamp(timestamp):
    """Return a naive utc datetime object."""
    if not timestamp:
        return timestamp
    if not isinstance(timestamp, datetime.datetime):
        timestamp = timeutils.parse_isotime(timestamp)
    return timeutils.normalize_time(timestamp)


def update_nested(original_dict, updates):
    """Updates the leaf nodes in a nest dict.

     Updates occur without replacing entire sub-dicts.
    """
    dict_to_update = copy.deepcopy(original_dict)
    for key, value in updates.items():
        if isinstance(value, dict):
            sub_dict = update_nested(dict_to_update.get(key, {}), value)
            dict_to_update[key] = sub_dict
        else:
            dict_to_update[key] = updates[key]
    return dict_to_update
