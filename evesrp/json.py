from __future__ import absolute_import
from flask import request
from flask.json import JSONEncoder
import six
from decimal import Decimal
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
            try:
                extended = request.json_extended
            except AttributeError:
                extended = request.args.get('extended', False)
            # request.json_extended can be a dict to set extended mode for only
            # certain types of objects
            if isinstance(extended, dict):
                scope_class = object
                scope_extended = False
                for cls, ext in six.iteritems(extended):
                    if isinstance(o, cls) and issubclass(type(o), scope_class):
                        scope_extended = ext
                        scope_class = cls
                extended = scope_extended
            return o._json(extended)
        return super(PrivateJsonEncoder, self).default(o)


class DecimalEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, PrettyDecimal):
            return o.currency()
        elif isinstance(o, Decimal):
            return unicode(o)
        return super(DecimalEncoder, self).default(o)


# Multiple inheritance FTW
class SRPEncoder(PrivateJsonEncoder, IterableEncoder, DecimalEncoder):
    pass
