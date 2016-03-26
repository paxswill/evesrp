from __future__ import absolute_import

"""Originally taken from http://techspot.zzzeek.org/2011/01/14/the-enum-recipe/
on 23 May 2014. Specifically, this is a modified version of
http://techspot.zzzeek.org/files/2011/decl_enum.py
"""

import six
from sqlalchemy.types import SchemaType
import re
from speaklater import is_lazy_string
from .unistr import unistr, ensure_unicode
from .. import db


if six.PY3:
    unicode = str


@unistr
class EnumSymbol(object):
    """Define a fixed symbol tied to a parent class."""

    def __init__(self, cls_, name, value, description):
        self.cls_ = cls_
        self.name = name
        self.value = value
        self.description = description

    def __reduce__(self):
        """Allow unpickling to return the symbol 
        linked to the DeclEnum class."""
        return getattr, (self.cls_, self.name)

    def __iter__(self):
        return iter([self.value, self.description])

    def __repr__(self):
        return u"<%s>" % self.name

    def __unicode__(self):
        if is_lazy_string(self.description):
            return unicode(self.description)
        return self.description

    def _json(self, extended=False):
        # Not going to account for inheritance, as nothing should be inheriting
        # from EnumSymbol
        return self.name


class EnumMeta(type):
    """Generate new DeclEnum classes."""

    def __init__(cls, classname, bases, dict_):
        cls._reg = reg = cls._reg.copy()
        for k, v in six.iteritems(dict_):
            if isinstance(v, tuple):
                unicoded = []
                for tup_v in v:
                    unicoded.append(ensure_unicode(tup_v))
                sym = reg[unicoded[0]] = EnumSymbol(cls, k, *unicoded)
                setattr(cls, k, sym)
        return type.__init__(cls, classname, bases, dict_)

    def __iter__(cls):
        return six.itervalues(cls._reg)


@six.add_metaclass(EnumMeta)
class DeclEnum(object):
    """Declarative enumeration."""

    _reg = {}

    @classmethod
    def from_string(cls, value):
        try:
            return cls._reg[ensure_unicode(value)]
        except KeyError:
            raise ValueError(
                    u"Invalid value for %r: %r" % 
                    (cls.__name__, ensure_unicode(value))
                )

    @classmethod
    def values(cls):
        return six.iterkeys(cls._reg)

    @classmethod
    def db_type(cls):
        return DeclEnumType(cls)


class DeclEnumType(SchemaType, db.TypeDecorator):
    def __init__(self, enum):
        self.enum = enum
        self.impl = db.Enum(
                        *(list(enum.values())),
                        convert_unicode=True,
                        name=u"ck%s" % re.sub(
                                    '([A-Z])', 
                                    lambda m:"_" + m.group(1).lower(), 
                                    enum.__name__)
                    )

    def _set_table(self, table, column):
        self.impl._set_table(table, column)

    def copy(self):
        return DeclEnumType(self.enum)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value.value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.enum.from_string(value.strip())
