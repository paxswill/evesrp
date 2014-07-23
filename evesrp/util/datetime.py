from __future__ import absolute_import

import datetime as dt
from sqlalchemy import types


class UTC(dt.tzinfo):

    def utcoffset(self, obj):
        return dt.timedelta()

    def dst(self, obj):
        return dt.timedelta()

    def tzname(self, obj):
        return u'UTC+00:00'


utc = UTC()


class DateTime(types.TypeDecorator):

    impl = types.DateTime

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'mysql':
            return dt.datetime(*(value.utctimetuple()[0:6]))
        return value
