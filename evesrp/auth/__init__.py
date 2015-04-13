from __future__ import absolute_import
import re

from flask import redirect, url_for, current_app
from flask.ext.login import current_user
import flask.ext.login as flask_login
from flask.ext.wtf import Form
from wtforms.fields import SubmitField, HiddenField
from ..util import DeclEnum, classproperty, ensure_unicode




class AuthMethod(object):
    """Represents an authentication mechanism for users."""

    def __init__(self, admins=None, name=u'Base Authentication', **kwargs):
        """
        :param admins: A list of usernames to treat as site-wide
            administrators. Useful for initial setup.
        :type admins: list
        :param str name: The user-facing name for this authentication method.
        """
        if admins is None:
            self.admins = []
        else:
            self.admins = admins
        self.name = ensure_unicode(name)

    def form(self):
        """Return a :py:class:`flask.ext.wtf.Form` subclass to login with."""
        class AuthForm(Form):
            submit = SubmitField(u'Log In using {}'.format(self.name))
        return AuthForm

    def login(self, form):
        """Process a validated login form.

        You must return a valid response object.
        """
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

        Handles calling :py:func:`flask.ext.login.login_user` and any other
        related housekeeping functions for you.

        :param user: The user that has been authenticated and is logging in.
        :type user: :py:class:`~models.User`
        """
        flask_login.login_user(user)

    @property
    def safe_name(self):
        """Normalizes a string to be a valid Python identifier (along with a few
        other things).

        Specifically, all letters are lower cased and non-ASCII and whitespace
        are replaced by underscores.

        :returns: The normalized string.
        :rtype str:
        """
        # Turn 'fancy' characters into '?'s
        ascii_rep = self.name.encode('ascii', 'replace').decode('utf-8')
        # Whitespace and '?' to underscores
        no_space = re.sub(r'[\s\?]', u'_', ascii_rep)
        lowered = no_space.lower()
        return lowered


class AnonymousUser(flask_login.AnonymousUserMixin):

    def has_permission(self, permissions, division_or_request=None):
        return False


class PermissionType(DeclEnum):
    """Enumerated type for the types of permissions available. """

    #: Permission allowing submission of :py:class:`~.Request`\s to a
    #: :py:class:`~.Division`.
    submit = u'submit', u'Submitter'

    #: Permission for reviewers of requests in a :py:class:`~.Division`.
    review = u'review', u'Reviewer'

    #: Permission for payers in a :py:class:`~.Division`.
    pay = u'pay', u'Payer'

    #: :py:class:`~.Division`\-level administrator permission
    admin = u'admin', u'Administrator'

    #: A special permission for allowing read-only elevated access
    audit = u'audit', u'Auditor'

    @classproperty
    def elevated(cls):
        return frozenset((cls.review, cls.pay, cls.admin, cls.audit))

    @classproperty
    def all(cls):
        return frozenset((cls.submit,
                          cls.review,
                          cls.pay,
                          cls.admin,
                          cls.audit))
