import flask
import flask_login
import six

from evesrp import new_models as models


if six.PY3:
    unicode = str


class LoginUser(flask_login.UserMixin):

    def __init__(self, user):
        self.user = user

    def get_id(self):
        return unicode(self.user.id_)

    def __getattr__(self, attr):
        return getattr(self.user, attr)

    def has_permission(self, permission_type, division_or_request=None):
        store = flask.current_app.store
        get_kwargs = {
            'entity_id': self.user.id_,
            'type_': permission_type,
        }
        if division_or_request is not None:
            if hasattr(division_or_request, 'division_id'):
                division_id = division_or_request.division_id
            else:
                division_id = division_or_request.id_
            get_kwargs['division_id'] = division_id
        permissions = list(store.get_permissions(**get_kwargs))
        return len(permissions) > 0


class AnonymousUser(flask_login.AnonymousUserMixin):

    def has_permission(self, permission_type, division_or_request=None):
        return False
