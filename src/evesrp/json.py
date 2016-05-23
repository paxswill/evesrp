from __future__ import absolute_import
from flask import request
from flask.json import JSONEncoder
import six
from decimal import Decimal
from datetime import datetime
from .util import PrettyDecimal

if six.PY3:
    unicode = str


class IterableEncoder(JSONEncoder):
    def default(self, o):
        try:
            iterator = iter(o)
        except TypeError:
            pass
        else:
            return list(o)
        return super(IterableEncoder, self).default(o)


class PrivateJsonEncoder(JSONEncoder):
    def default(self, o):
        if hasattr(o, '_json'):
            return o._json()
        return super(PrivateJsonEncoder, self).default(o)


class DecimalEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, PrettyDecimal):
            return o.currency()
        elif isinstance(o, Decimal):
            return unicode(o)
        return super(DecimalEncoder, self).default(o)


class TimestampEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super(TimestampEncoder, self).default(o)


# Multiple inheritance FTW
class SRPEncoder(PrivateJsonEncoder, IterableEncoder, DecimalEncoder,
                 TimestampEncoder):
    pass
