import re

from flask import redirect, url_for, current_app
from flask.ext.login import current_user
import flask.ext.login as flask_login
from flask.ext.wtf import Form
from wtforms.fields import SubmitField, HiddenField
from ..util import DeclEnum, classproperty


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


class PermissionType(DeclEnum):
    submit = 'submit', 'Submitter'
    review = 'review', 'Reviewer'
    pay = 'pay', 'Payer'
    admin = 'admin', 'Administrator'

    @classproperty
    def elevated(cls):
        return frozenset((cls.review, cls.pay, cls.admin))

    @classproperty
    def all(cls):
        return frozenset((cls.submit, cls.review, cls.pay, cls.admin))
