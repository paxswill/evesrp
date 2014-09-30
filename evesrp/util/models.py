from __future__ import absolute_import
from __future__ import unicode_literals
import datetime as dt
from sqlalchemy.types import DateTime
from sqlalchemy.ext.declarative import declared_attr
from .datetime import DateTime
from .datetime import utc
from .. import db


class AutoID(object):
    """Mixin adding a primary key integer column named 'id'."""
    id = db.Column(db.Integer, primary_key=True)

    def _json(self, extended=False):
        try:
            parent = super(AutoName, self)._json(extended)
        except AttributeError:
            parent = {}
        parent[u'id'] = self.id
        return parent


def _utcnow(arg):
    return dt.datetime.now(utc)

class Timestamped(object):
    """Mixin adding a timestamp column.

    The timestamp defaults to the current time.
    """
    timestamp = db.Column(DateTime, nullable=False,
            default=_utcnow)


class AutoName(object):

    @declared_attr
    def __tablename__(cls):
        """SQLAlchemy late-binding attribute to set the table name.

        Implemented this way so subclasses do not need to specify a table name
        themselves.
        """
        return cls.__name__.lower()
