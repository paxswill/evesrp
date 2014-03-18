import re
from collections import namedtuple
from functools import partial

from flask.ext.login import current_user
from flask.ext.principal import Permission, UserNeed, RoleNeed, identity_loaded

from . import app, db, login_manager, principal
from .models import User, Group, Division


class AuthMethod(object):
    method_name = 'Base Authentication'

    @classmethod
    def authenticate_user(cls, user):
        pass

    @classmethod
    def list_groups(cls, user=None):
        pass


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
PayoutRequestsNeed = partial(ReimbursementNeed, 'payout')


# Now, create Permission classes for these kinds of needs.
class SubmitRequestsPermission(Permission):
    def __init__(self, division):
        need = SubmitRequestsNeed(division.id)
        super(SubmitRequestsPermission, self).__init__(need)


class ReviewRequestsPermission(Permission):
    def __init__(self, division):
        need = ReviewRequestsNeed(division.id)
        super(ReviewRequestsPermission, self).__init__(need)


class PayoutRequestsPermission(Permission):
    def __init__(self, division):
        need = PayoutRequestsNeed(division.id)
        super(PayoutRequestsPermission, self).__init__(need)


@identity_loaded.connect_via(app)
def load_user_permissions(sender, identity):
    identity.user = current_user

    # Set user role (see and modify their own requests)j
    identity.provides.add(UserNeed(current_user.id))

    # Set division roles
    for role in ('submit', 'review', 'payout'):
        for division in current_user.divisions[role]:
            identity.provides.add(ReimbursementNeed(role, division.id))

    # If they're an admin, set that
    if current_user.full_admin:
        identity.provides.add(RoleNeed('admin'))
    if current_user.division_admin:
        identity.provides.add(RoleNeed('claimer'))
