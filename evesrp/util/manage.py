#!/usr/bin.env python

import os
import os.path
import argparse
import flask
from flask.ext import script
from flask.ext.migrate import Migrate, MigrateCommand, _get_config, stamp
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from .. import create_app, db, migrate


manager = script.Manager(create_app)


class AbsolutePathAction(argparse.Action):
    """Custom argparse.Action that transforms path strings into absolute paths.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        current_absolute = os.path.abspath(os.getcwd())
        if isinstance(values, str):
            new_values = os.path.join(current_absolute, values)
        else:
            new_values = []
            for value in values:
                real_path = os.path.join(current_absolute, values)
                new_values.append(real_path)
        setattr(namespace, self.dest, new_values)


# Monkeypatch Flask-Script to consider my custom path action 'safe'
safe_actions = list(script.safe_actions)
safe_actions.append(AbsolutePathAction)
script.safe_actions = safe_actions


# Crufty workaround to get Flask-Migrate working with app factories
class MigrateManager(script.Manager):
    def __init__(self, old_command, directory='migrations'):
        super(MigrateManager, self).__init__()
        self.directory = directory
        for attr in ('app', '_commands', '_options', 'usage', 'help',
                'description', 'disable_argcomplete', 'with_default_commands',
                'parent'):
            setattr(self, attr, getattr(old_command, attr))

    def __call__(self, app=None, directory='migrations', **kwargs):
        if app is None:
            app = self.app
            if app is None:
                raise Exception("No app specified")

        db = kwargs.pop('db', None)

        if not isinstance(app, flask.Flask):
            app = app(**kwargs)

        # Last ditch effort to get a database handle
        if db is None:
            if 'sqlalchemy' in app.extensions:
                db = app.extensions['sqlalchemy'].db
            else:
                raise Exception("No database defined for app.")

        Migrate(app, db, self.directory)
        return app


migrate_path = os.path.dirname(migrate.__file__)
migrate_path = os.path.abspath(migrate_path)
migrate_manager = MigrateManager(MigrateCommand, migrate_path)
manager.add_command('db', migrate_manager)


manager.add_option('-c', '--config', dest='config', required=True,
        action=AbsolutePathAction)


@migrate_manager.command
def create(force=False):
    """Create tables if the database has not been configured yet."""
    # Fail if there's an alembic version set
    engine = db.get_engine(flask.current_app)
    conn = engine.connect()
    context = MigrationContext.configure(conn)
    current_rev = context.get_current_revision()
    alembic_config = _get_config(directory=migrate_path)
    script = ScriptDirectory.from_config(alembic_config)
    latest_rev = script.get_current_head()
    if current_rev == latest_rev and not force:
        print("You need to run 'evesrp -c config.py db migrate' to "
              "migrate to the latest database schema.")
    else:
        db.create_all()
        if current_rev is None:
            stamp()


def main():
    manager.run()


if __name__ == '__main__':
    main()
