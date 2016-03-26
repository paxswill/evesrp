#!/usr/bin.env python

from __future__ import absolute_import
from __future__ import print_function
import os
import os.path
import argparse
from itertools import cycle
import json
from decimal import Decimal
import time
import datetime as dt
import flask
from flask.ext import script
from flask.ext.migrate import Migrate, MigrateCommand, stamp
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
import six
from .. import create_app, db, migrate, models, auth, killmail
from .datetime import utc


if six.PY3:
    unicode = str


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
                raise Exception(u"No app specified")

        db = kwargs.pop('db', None)

        if not isinstance(app, flask.Flask):
            app = app(**kwargs)

        # Last ditch effort to get a database handle
        if db is None:
            if 'sqlalchemy' in app.extensions:
                db = app.extensions['sqlalchemy'].db
            else:
                raise Exception(u"No database defined for app.")

        Migrate(app, db, self.directory)
        return app


migrate_path = os.path.dirname(migrate.__file__)
migrate_path = os.path.abspath(migrate_path)
migrate_manager = MigrateManager(MigrateCommand, migrate_path)
manager.add_command('db', migrate_manager)


manager.add_option('-c', '--config', dest='config', required=False,
        action=AbsolutePathAction)
manager.add_option('-i', '--instance', dest='instance_path', required=False,
        action=AbsolutePathAction)


@migrate_manager.command
def create(force=False):
    """Create tables if the database has not been configured yet."""
    # Fail if there's an alembic version set
    engine = db.get_engine(flask.current_app)
    conn = engine.connect()
    context = MigrationContext.configure(conn)
    current_rev = context.get_current_revision()
    alembic_config = flask.current_app.extensions['migrate'].migrate.get_config(
            directory=migrate_path)
    script = ScriptDirectory.from_config(alembic_config)
    latest_rev = script.get_current_head()
    if current_rev == latest_rev and not force:
        print(u"You need to run 'evesrp -c config.py db migrate' to "
              u"migrate to the latest database schema.")
    else:
        db.create_all()
        if current_rev is None:
            stamp()


@manager.shell
def shell_context():
    ctx = dict(
        app=flask.current_app,
        db=db)
    for cls in ('Request', 'Action', 'ActionType', 'Modifier',
                'AbsoluteModifier', 'RelativeModifier'):
        ctx[cls] = getattr(models, cls)
    for cls in ('Entity', 'User', 'Group', 'Note', 'APIKey', 'Permission',
            'Division', 'Pilot'):
        ctx[cls] = getattr(auth.models, cls)
    ctx['PermissionType'] = auth.PermissionType
    return ctx


class PopulatedKillmail(killmail.Killmail, killmail.RequestsSessionMixin,
        killmail.ShipNameMixin, killmail.LocationMixin):
    pass


class Populate(script.Command):
    """Populate the database with data given from a list of losses form zKB."""

    option_list = (
        script.Option('--file', '-f', dest='kill_file', required=True),
        script.Option('--users', '-u', dest='num_users', default=5, type=int),
        script.Option('--divisions', '-d', dest='num_divisions', default=3,
                type=int),
    )

    def run(self, kill_file, num_users, num_divisions, **kwargs):
        # Set up users, divisions and permissions
        users = []
        for user_num, authmethod in zip(range(num_users),
                cycle(flask.current_app.config['SRP_AUTH_METHODS'])):
            user_name = u'User {}'.format(user_num)
            user = auth.models.User.query.filter_by(name=user_name).first()
            if user is None:
                user = auth.models.User(user_name, authmethod.name)
                db.session.add(user)
            users.append(user)
        divisions = []
        for division_num in range(num_divisions):
            division_name = u'Division {}'.format(division_num)
            division = auth.models.Division.query.filter_by(
                    name=division_name).first()
            if division is None:
                division = auth.models.Division(division_name)
                db.session.add(division)
            divisions.append(division)
        db.session.add_all(divisions)
        for user in users:
            for division in divisions:
                perm = auth.models.Permission.query.filter_by(division=division,
                        permission=auth.PermissionType.submit,
                        entity=user).first()
                if perm is None:
                    auth.models.Permission(division,
                            auth.PermissionType.submit, user)
        db.session.commit()
        # load and start processing killmails
        with open(kill_file, 'r') as f:
            kills = json.load(f)
        for user, division, kill_info in zip(cycle(users), cycle(divisions), kills):
            victim = kill_info[u'victim']
            # Skip corp-level kills (towers, pocos, etc)
            if victim['characterID'] == '0':
                continue
            # make sure a Pilot exists for this killmail
            pilot = auth.models.Pilot.query.get(victim['characterID'])
            if pilot is None:
                pilot = auth.models.Pilot(user, victim['characterName'],
                        int(victim['characterID']))
            db.session.commit()
            pilot_user = pilot.user
            # create a Killmail
            args = dict(
                    kill_id=int(kill_info[u'killID']),
                    pilot_id=int(victim[u'characterID']),
                    pilot=victim[u'characterName'],
                    corp_id=int(victim[u'corporationID']),
                    corp=victim[u'corporationName'],
                    ship_id=int(victim[u'shipTypeID']),
                    system_id=int(kill_info[u'solarSystemID']),
                    verified=True)
            if victim[u'allianceID'] != '0':
                args['alliance_id'] = int(victim[u'allianceID'])
                args['alliance'] = victim[u'allianceName']
            time_struct = time.strptime(kill_info[u'killTime'], '%Y-%m-%d %H:%M:%S')
            args['timestamp'] = dt.datetime(*(time_struct[0:6]), tzinfo=utc)
            args['url'] = u'https://zkillboard.com/kill/{}'.format(
                    args['kill_id'])
            try:
                args['value'] = Decimal(kill_info[u'zkb'][u'totalValue'])
            except KeyError:
                args['value'] = Decimal(0)
            killmail = PopulatedKillmail(**args)
            try:
                killmail.ship
            except KeyError:
                continue
            # Create a request for this killmail
            models.Request(pilot_user, unicode(killmail), division, killmail)
            db.session.commit()


manager.add_command('populate', Populate())


def main():
    manager.run()


if __name__ == '__main__':
    main()
