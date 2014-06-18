import datetime as dt
from sqlalchemy.types import DateTime
from sqlalchemy.ext.declarative import declared_attr
from .. import db


class AutoID(object):
    """Mixin adding a primary key integer column named 'id'."""
    id = db.Column(db.Integer, primary_key=True)


class Timestamped(object):
    """Mixin adding a timestamp column.

    The timestamp defaults to the current time.
    """
    timestamp = db.Column(DateTime, nullable=False,
            default=dt.datetime.utcnow())


class AutoName(object):

    @declared_attr
    def __tablename__(cls):
        """SQLAlchemy late-binding attribute to set the table name.

        Implemented this way so subclasses do not need to specify a table name
        themselves.
        """
        return cls.__name__.lower()
