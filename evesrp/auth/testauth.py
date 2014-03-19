import hashlib

from sqlalchemy.orm.exc import NoResultFound

from .. import db, requests_session
from . import AuthMethod
from .models import User, Group


class TestAuth(AuthMethod):
    method_name = "Test Auth"

    @classmethod
    def authenticate_user(cls, user, password):
        """Authenticate a user.

        If the corresponding user has a User object, return that. Otherwise,
        create a new one.
        """
        sha = hashlib.sha1()
        sha.update(password.encode())
        params = {
                'user': user,
                'pass': sha.hexdigest()
                }
        response = requests_session.get(
                'https://auth.pleaseignore.com/api/1.0/login',
                params=params)
        json = response.json()
        if json['auth'] != 'ok':
            return None
        try:
            user = TestAuthUser.query.filter_by(auth_id=json['id']).one()
        except NoResultFound:
            # Create new User
            user_args = {}
            user_args['username'] = json['username']
            user_args['auth_id'] = json['id']
            user = TestAuthUser(**user_args)
            db.session.add(user)
        # Update values from Auth
        user.admin = json['superuser'] or json['staff']
        for group in json['groups']:
            try:
                db_group = TestAuthGroup.query.filter_by(auth_id=group['id'])\
                        .one()
            except NoResultFound:
                db_group = TestAuthGroup(name=group['name'],
                        auth_id=group['id'])
                db.session.add(db_group)
            user.groups.append(db_group)
        db.session.commit()
        return user

    @classmethod
    def list_groups(cls, user=None):
        """Return a list of groups descriptors.

        If user is None, return _all_ groups. Otherwise, return the groups a
        member is part of.
        """
        if user is None:
            response = requests_session.get(
                    'https://auth.pleaseignore.com/api/1.0/info',
                    params={'request': 'groups'})
            # TODO Handle possible errors
            groups = set()
            for group in response.json():
                group_tuple = (group['name'], cls.__name__)
                groups.add(group_tuple)
            return groups
        else:
            # NOTE: THis might not be a secure/proper check. Test it.
            if user.authmethod() != cls:
                # TODO: Raise an exception here, this is the wrong authmethod
                # for this user.
                return None
            # TODO: Needs an Auth API key passed in somehow
            response = requests_session.get(
                    'https://auth.pleaseignore.com/api/1.0/user',
                    params={'userid': user.auth_id(), 'apikey': None})
            groups = set()
            for group in response.json()['groups']:
                group_tuple = (group['name'], cls.__name__)
                groups.add(group_tuple)
            return groups


class TestAuthUser(User):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    auth_id = db.Column(db.Integer, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)

    def __init__(self, username, auth_id, groups=None, **kwargs):
        self.name = username
        self.auth_id = auth_id

    @classmethod
    def authmethod(cls):
        return TestAuth

class TestAuthGroup(Group):
    id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    auth_id = db.Column(db.Integer, nullable=False, index=True)
    description = db.Column(db.Text)

    def __init__(self, name, auth_id):
        self.name = name
        self.auth_id = auth_id

    @classmethod
    def authmethod(cls):
        return TestAuth
