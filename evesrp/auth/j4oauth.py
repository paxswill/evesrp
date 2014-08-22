from flask import current_app, redirect, url_for, flash, session
from copy import deepcopy
from sqlalchemy.orm.exc import NoResultFound

from .. import db, oauth
from . import AuthMethod
from .models import User, Group, Pilot

def tokengetter():
    return session.get('j4lp_token', None)


class J4OAuth(AuthMethod):
    def __init__(self, key, secret, base_url, 
                 access_token_url, authorize_url, **kwargs):
        self.j4lp = oauth.remote_app('j4lp',
            base_url=base_url,
            request_token_url=None,
            access_token_url=access_token_url,
            access_token_method='GET',
            authorize_url=authorize_url,
            consumer_key=key,
            consumer_secret=secret,
            request_token_params={'scope': ['auth_info', 'auth_groups',
                                            'characters']},
        )
        
        if 'name' not in kwargs:
            kwargs['name'] = 'J4LP'
        
        self.view = self.j4lp.authorized_handler(self.view)
        self.j4lp.tokengetter(tokengetter)

        super(J4OAuth, self).__init__(**kwargs)
        
    def login(self, form):
        redirect_url = url_for('login.auth_method_login', _external=True, 
                               auth_method=self.safe_name)
        return self.j4lp.authorize(callback=redirect_url)
    
    def list_groups(self, user=None):
        # i don't even know what this does
        # thanks brave
        pass

    def view(self, res):
        if res is None:
            flash('Auth denied', 'danger')
            return redirect(url_for('login.login'))
        
        session['j4lp_token'] = (res['access_token'], '')
        auth_user = self.j4lp.get('auth_user').data['user']
        try:
            user = J4LPUser.query.filter_by(name=auth_user['main_character'],
                                            authmethod=self.name).one()
        except NoResultFound:
            user = J4LPUser(name=auth_user['main_character'], authmethod=self.name)
            db.session.add(user)
        user.admin = user.name in self.admins

        auth_groups = self.j4lp.get('auth_groups').data['groups']
        auth_groups.append('{} alliance'.format(auth_user['alliance']))

        for group_name in auth_groups:
            try:
                group = J4LPGroup.query.filter_by(name=group_name,
                                                  authmethod=self.name).one()
            except NoResultFound:
                group = J4LPGroup(group_name, self.name)
                db.session.add(group)
            user.groups.add(group)

        user_groups = deepcopy(user.groups)
        for group in user_groups:
            if group.name not in auth_groups and group in user.groups:
                user.groups.remove(group)
        
        print(self.j4lp.get('characters').data['characters'])

        pilot = Pilot.query.get(auth_user['main_character_id'])
        if not pilot:
            pilot = Pilot(user, auth_user['main_character'],
                          auth_user['main_character_id'])
            db.session.add(pilot)
        else:
            pilot.user = user
        db.session.commit()
        self.login_user(user)
        return redirect(url_for('index'))

#            info = self.api.core.info(token=token)
#            char_name = info.character.name
#            try:
#                user = CoreUser.query.filter_by(name=char_name,
#                        authmethod=self.name).one()
#                user.token = token
#            except NoResultFound:
#                user = CoreUser(name=char_name, authmethod=self.name,
#                        token=token)
#                db.session.add(user)
#            # Apply admin flag
#            user.admin = user.name in self.admins
#            # Sync up group membership
#            for group_name in info.tags:
#                try:
#                    group = CoreGroup.query.filter_by(name=group_name,
#                            authmethod=self.name).one()
#                except NoResultFound:
#                    group = CoreGroup(group_name, self.name)
#                    db.session.add(group)
#                user.groups.add(group)
#            user_groups = deepcopy(user.groups)
#            for group in user_groups:
#                if group.name not in info.tags and group in user.groups:
#                    user.groups.remove(group)
#            # Sync pilot (just the primary for now)
#            pilot = Pilot.query.get(info.character.id)
#            if not pilot:
#                pilot = Pilot(user, char_name, info.character.id)
#                db.session.add(pilot)
#            else:
#                pilot.user = user
#            db.session.commit()
#            self.login_user(user)
#            # TODO Have a meaningful redirect for this
#            return redirect(url_for('index'))
#        else:
#            flash(u"Login failed.", u'error')
#            return redirect(url_for('login.login'))
#
#
class J4LPUser(User):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)


class J4LPGroup(Group):
    id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    description = db.Column(db.Text(convert_unicode=True))
