from __future__ import absolute_import
import re

from flask import redirect, url_for, current_app
from flask.ext.babel import gettext, lazy_gettext
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
            submit = SubmitField(gettext(
                    u'Log In using %(authmethod_name)s',
                    authmethod_name=self.name))
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

    # TRANS: The title for someone who is able to submit a request to a
    # TRANS: division.
    submit = u'submit', lazy_gettext(u'Submitter')
    """Permission allowing submission of :py:class:`~.Request`\s to a
    :py:class:`~.Division`.
    """

    # TRANS: The title for someone who is able to review requests to a
    # TRANS: division.
    review = u'review', lazy_gettext(u'Reviewer')
    """Permission for reviewers of requests in a :py:class:`~.Division`."""

    # TRANS: The title form someone who is able to mark requests as paid in a
    # TRANS: division.
    pay = u'pay', lazy_gettext(u'Payer')
    """Permission for payers in a :py:class:`~.Division`."""

    # TRANS: The title for someone who is able to administer a division.
    admin = u'admin', lazy_gettext(u'Administrator')
    """:py:class:`~.Division`\-level administrator permission"""

    # TRANS: The title for someone who is able to audit the activities of a
    # TRANS: division. This means they are able to view all requests in a
    # TRANS: division.
    audit = u'audit', lazy_gettext(u'Auditor')
    """A special permission for allowing read-only elevated access"""

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
