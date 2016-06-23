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
SQLAlchemy models for Panko data.
"""
import json

import six
import sqlalchemy
from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy import Float, DateTime
from sqlalchemy.dialects.mysql import DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import deferred
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from panko import utils


class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string."""

    impl = sqlalchemy.Text

    @staticmethod
    def process_bind_param(value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    @staticmethod
    def process_result_value(value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class PreciseTimestamp(TypeDecorator):
    """Represents a timestamp precise to the microsecond."""

    impl = DateTime

    def load_dialect_impl(self, dialect):
        if dialect.name == 'mysql':
            return dialect.type_descriptor(DECIMAL(precision=20,
                                                   scale=6,
                                                   asdecimal=True))
        return self.impl

    @staticmethod
    def process_bind_param(value, dialect):
        if value is None:
            return value
        elif dialect.name == 'mysql':
            return utils.dt_to_decimal(value)
        return value

    @staticmethod
    def process_result_value(value, dialect):
        if value is None:
            return value
        elif dialect.name == 'mysql':
            return utils.decimal_to_dt(value)
        return value


class PankoBase(object):
    """Base class for Panko Models."""
    __table_args__ = {'mysql_charset': "utf8",
                      'mysql_engine': "InnoDB"}
    __table_initialized__ = False

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def update(self, values):
        """Make the model object behave like a dict."""
        for k, v in six.iteritems(values):
            setattr(self, k, v)


Base = declarative_base(cls=PankoBase)


class EventType(Base):
    """Types of event records."""
    __tablename__ = 'event_type'

    id = Column(Integer, primary_key=True)
    desc = Column(String(255), unique=True)

    def __init__(self, event_type):
        self.desc = event_type

    def __repr__(self):
        return "<EventType: %s>" % self.desc


class Event(Base):
    __tablename__ = 'event'
    __table_args__ = (
        Index('ix_event_message_id', 'message_id'),
        Index('ix_event_type_id', 'event_type_id'),
        Index('ix_event_generated', 'generated')
    )
    id = Column(Integer, primary_key=True)
    message_id = Column(String(50), unique=True)
    generated = Column(PreciseTimestamp())
    raw = deferred(Column(JSONEncodedDict()))

    event_type_id = Column(Integer, ForeignKey('event_type.id'))
    event_type = relationship("EventType", backref='events')

    def __init__(self, message_id, event_type, generated, raw):
        self.message_id = message_id
        self.event_type = event_type
        self.generated = generated
        self.raw = raw

    def __repr__(self):
        return "<Event %d('Event: %s %s, Generated: %s')>" % (self.id,
                                                              self.message_id,
                                                              self.event_type,
                                                              self.generated)


class TraitText(Base):
    """Event text traits."""

    __tablename__ = 'trait_text'
    __table_args__ = (
        Index('ix_trait_text_event_id_key', 'event_id', 'key'),
    )
    event_id = Column(Integer, ForeignKey('event.id'), primary_key=True)
    key = Column(String(255), primary_key=True)
    value = Column(String(255))


class TraitInt(Base):
    """Event integer traits."""

    __tablename__ = 'trait_int'
    __table_args__ = (
        Index('ix_trait_int_event_id_key', 'event_id', 'key'),
    )
    event_id = Column(Integer, ForeignKey('event.id'), primary_key=True)
    key = Column(String(255), primary_key=True)
    value = Column(Integer)


class TraitFloat(Base):
    """Event float traits."""

    __tablename__ = 'trait_float'
    __table_args__ = (
        Index('ix_trait_float_event_id_key', 'event_id', 'key'),
    )
    event_id = Column(Integer, ForeignKey('event.id'), primary_key=True)
    key = Column(String(255), primary_key=True)
    value = Column(Float(53))


class TraitDatetime(Base):
    """Event datetime traits."""

    __tablename__ = 'trait_datetime'
    __table_args__ = (
        Index('ix_trait_datetime_event_id_key', 'event_id', 'key'),
    )
    event_id = Column(Integer, ForeignKey('event.id'), primary_key=True)
    key = Column(String(255), primary_key=True)
    value = Column(PreciseTimestamp())
