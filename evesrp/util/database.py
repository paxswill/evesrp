from __future__ import absolute_import
import os.path
from flask.ext.migrate import _get_config, stamp
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
import flask
from .unistr import unistr
from .. import db, migrate


migrate_path = os.path.dirname(migrate.__file__)
migrate_path = os.path.abspath(migrate_path)


def get_current(app):
    """Get the current database schema revision identifier."""
    engine = db.get_engine(app)
    conn = engine.connect()
    context = MigrationContext.configure(conn)
    current_rev = context.get_current_revision()
    return current_rev


def get_latest(app):
    """Get the latest database schema revision identifier."""
    alembic_config = _get_config(directory=migrate_path)
    script = ScriptDirectory.from_config(alembic_config)
    latest_rev = script.get_current_head()
    return latest_rev


def is_current(app):
    """Check to see if the database schema version is the latest version."""
    return get_current(app) == get_latest(app)


def create_all(bind='__all__', app=None):
    """Create the database schema and set the current version to the latest."""
    db.create_all(bind, app)
    if current_rev is None:
        stamp(directory=migrate_path)
