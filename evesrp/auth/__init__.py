import re
from collections import namedtuple
from functools import partial

from flask import redirect, url_for, current_app
from flask.ext.login import current_user
import flask.ext.login as flask_login
from flask.ext.principal import Permission, UserNeed, RoleNeed,\
        identity_loaded, identity_changed, Identity, Principal
from flask.ext.wtf import Form
from wtforms.fields import SubmitField, HiddenField

from ..models import db
from ..views.login import login_manager


principal = Principal()


class AuthForm(Form):
    submit = SubmitField('Login')


class AuthMethod(object):
    def __init__(self, admins=None, name='Base Authentication', **kwargs):
        if admins is None:
            self.admins = []
        else:
            self.admins = admins
        self.name = name

    def form(self):
        """Return a form class to login with."""
        return AuthForm

    def login(self, form):
        """Process a validated login form.

        You must return a valid response object.
        """
        pass

    def list_groups(self, user=None):
        pass

    def view(self):
        """Optional method for providing secondary views.

        :py:func:`evesrp.views.login.auth_method_login` is configured to allow
        both GET and POST requests, and will call this method as soon as it is
        known which auth method is meant to be called. The path for this view
        is ``/login/self.safe_name/``, and can be generated with
        ``url_for('login.auth_method_login', auth_method=self.safe_name)``.

        The default implementation redirects to the main login view.
        """
        return redirect(url_for('login.login'))

    @staticmethod
    def login_user(user):
        """Signal to the authentication systems that a new user has logged in.

        Handles sending the :py:data:`flask.ext.principal.identity_changed`
        signal and calling :py:func:`flask.ext.login.login_user` for you.

        :param user: The user that has been authenticated and is logging in.
        :type user: :py:class:`~models.User`
        """
        flask_login.login_user(user)
        identity_changed.send(current_app._get_current_object(),
                identity=Identity(user.id))

    @property
    def safe_name(self):
        """Normalizes a string to be a valid Python identifier (along with a few
        other things).

        Specifically, all letters are lower cased, only ASCII characters, and
        whitespace replaced by underscores.

        :returns: The normalized string.
        :rtype str:
        """
        # Turn 'fancy' characters into '?'s
        ascii_rep = self.name.encode('ascii', 'replace').decode('utf-8')
        # Whitespace and '?' to underscores
        no_space = re.sub(r'[\s\?]', '_', ascii_rep)
        lowered = no_space.lower()
        return lowered


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


admin_permission = Permission(RoleNeed('admin'))


def load_user_permissions(sender, identity):
    identity.user = current_user

    if current_user.is_authenticated():
        # Set user role (see and modify their own requests)j
        identity.provides.add(UserNeed(current_user.id))

        # Set division roles
        for perm in current_user.permissions:
            identity.provides.add(ReimbursementNeed(perm.permission,
                    perm.division.id))

        # If they're an admin, set that
        if current_user.admin:
            identity.provides.add(RoleNeed('admin'))
