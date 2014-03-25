import re
from collections import namedtuple
from functools import partial

from flask.ext.login import current_user
from flask.ext.principal import Permission, UserNeed, RoleNeed, identity_loaded
from flask.ext.wtf import Form
from wtforms.fields import SubmitField, HiddenField

from .. import app, db, login_manager, principal


class AuthForm(Form):
    submit = SubmitField('Login')

    @classmethod
    def append_field(cls, name, field):
        setattr(cls, name, field)
        return cls


class AuthMethod(object):
    name = 'Base Authentication'

    def form(self):
        """Return an instance of the form to login."""
        return AuthForm.append_field('auth_method',
                HiddenField(default=self.name))

    def login(self, form):
        """Process a validated login form.

        You must return a valid response object.
        """
        pass

    def list_groups(self, user=None):
        pass

    @classmethod
    def register_views(cls, app):
        """Register views (if needed).

        This is an optional method to implement.
        """
        pass


# Work around some circular imports
from .models import User, Group, Division


@login_manager.user_loader
def login_loader(userid):
    """Pull a user object from the database.

    This is used for loading users from existing sessions.
    """
    return User.query.get(int(userid))


# This can be confusing, so here goes. Needs really only need to be tuples, of
# some unspecified (but known) length. So, we create named tuples, and then to
# make creating them easier freeze the first argument using partial.
ReimbursementNeed = namedtuple('ReimbursementNeed', ['method', 'division'])
SubmitRequestsNeed = partial(ReimbursementNeed, 'submit')
ReviewRequestsNeed = partial(ReimbursementNeed, 'review')
PayoutRequestsNeed = partial(ReimbursementNeed, 'pay')


# Now, create Permission classes for these kinds of needs.
class SubmitRequestsPermission(Permission):
    def __init__(self, div_or_request):
        if isinstance(div_or_request, Division):
            need = SubmitRequestsNeed(div_or_request.id)
        else:
            need = SubmitRequestsNeed(div_or_request.division.id)
        super(SubmitRequestsPermission, self).__init__(need)


class ReviewRequestsPermission(Permission):
    def __init__(self, div_or_request):
        if isinstance(div_or_request, Division):
            need = ReviewRequestsNeed(div_or_request.id)
        else:
            need = ReviewRequestsNeed(div_or_request.division.id)
        super(ReviewRequestsPermission, self).__init__(need)


class PayoutRequestsPermission(Permission):
    def __init__(self, div_or_request):
        if isinstance(div_or_request, Division):
            need = PayoutRequestsNeed(div_or_request.id)
        else:
            need = PayoutRequestsNeed(div_or_request.division.id)
        super(PayoutRequestsPermission, self).__init__(need)


@identity_loaded.connect_via(app)
def load_user_permissions(sender, identity):
    identity.user = current_user

    if current_user.is_authenticated():
        # Set user role (see and modify their own requests)j
        identity.provides.add(UserNeed(current_user.id))

        # Set division roles
        for role in ('submit', 'review', 'pay'):
            for division in current_user.divisions[role]:
                identity.provides.add(ReimbursementNeed(role, division.id))

        # If they're an admin, set that
        if current_user.admin:
            identity.provides.add(RoleNeed('admin'))
