from __future__ import absolute_import
from flask import flash, redirect, current_app, url_for, request
from flask.ext.login import current_user
from flask.ext.oauthlib.client import OAuthException
from flask.ext.wtf import csrf
from sqlalchemy.orm.exc import NoResultFound

from .. import db, oauth
from ..util import ensure_unicode
from . import AuthMethod
from .models import User, Group, Pilot


def token_getter():
    """Simple function to retrieve an access token from the current logged in
    user.
    """
    return {'access_token': current_user.token}


class OAuthMethod(AuthMethod):

    def __init__(self, **kwargs):
        """Abstract :py:class:`~.AuthMethod` for OAuth-based login methods.

        Implementing classes need to implement :py:meth:`get_user`\,
        :py:meth:`get_pilots`\, and :py:meth:`get_groups`\.

        In addition to the keyword arguments from :py:class:`~.AuthMethod`,
        this initializer accepts the following arguments that will be used in
        the creation of the :py:attr:`OAuthMethod.oauth` object (See the
        documentation for :py:class:`~flask_oauthlib.client.OAuthRemoteApp` for
        more details):

        * ``base_url``
        * ``request_token_url``
        * ``access_token_url``
        * ``authorize_url``
        * ``consumer_key``
        * ``consumer_secret``
        * ``request_token_params``
        * ``access_token_params``
        * ``access_token_method``
        * ``content_type``
        * ``app_key``
        * ``encoding``

        As a convenience, the ``key`` and ``secret`` keyword arguments will be
        treated as ``consumer_key`` and ``consumer_secret`` respectively. The
        ``name`` argument is used for both :py:class:`~.AuthMethod` and for
        :py:class:`~flask_oauthlib.client.OAuthRemoteApp`.

        Subclasses for providers that may be used by more than one entity are
        encouraged to provide their own defaults for the above arguments.

        The redirect URL for derived classes is based off of the
        :py:attr:`~.AuthMethod.safe_name` of the implementing
        :py:class:`~.AuthMethod`, specifically the URL for
        :py:meth:`~.AuthMethod.view`. For example, the default redirect URL for
        :py:class:`~.TestOAuth` is similar to
        ``https://example.com/login/test_oauth/`` (Note the trailing slash, it
        is significant).
        """
        # Allow using 'secret' and 'key' instead of 'consumer_[secret|key]'
        if 'key' in kwargs:
            kwargs['consumer_key'] = kwargs.pop('key')
        if 'secret' in kwargs:
            kwargs['consumer_secret'] = kwargs.pop('secret')
        # Remove OAuth arguments and create an arguments dictionary for them
        oauth_kwargs = {}
        for kwarg in ('oauth', 'base_url', 'request_token_url',
                      'access_token_url', 'authorize_url', 'consumer_key',
                      'consumer_secret', 'request_token_params',
                      'access_token_params', 'access_token_method',
                      'content_type', 'app_key', 'encoding'):
            if kwarg in kwargs:
                oauth_kwargs[kwarg] = kwargs.pop(kwarg)
        if 'name' not in kwargs:
            self.name = 'OAuth'
        else:
            self.name = kwargs['name']
        oauth_kwargs['name'] = self.name
        self.oauth = oauth.remote_app(**oauth_kwargs)
        self.oauth.tokengetter(token_getter)
        self.scope = kwargs.pop('scope', None)
        super(OAuthMethod, self).__init__(**kwargs)

    def login(self, form):
        # CSRF token valid for 5 minutes
        csrf_token = csrf.generate_csrf(time_limit=300)
        resp = self.oauth.authorize(callback=url_for('login.auth_method_login',
                                    auth_method=self.safe_name,
                                    _external=True), state=csrf_token)
        current_app.logger.debug(u"Redirecting to : {}".format(resp.location))
        return resp

    def view(self):
        """Handle creating and/or logging in the user and updating their
        :py:class:`~.Pilot`\s and :py:class:`~.Group`\s.
        """
        resp = self.oauth.authorized_response()
        # Check that the response was successful
        # Yeah, an exception as a return value. I don't know either.
        if isinstance(resp, OAuthException):
            flash(u"Login failed: {} ({})".format(resp.type, resp.message),
                    u'error')
            return redirect(url_for('login.login'))
        # Handle other kinds of errors
        elif resp is None:
            reason = ensure_unicode(request.args.get('error',
                    u'Unknown error'))
            if reason == u'access_denied':
                reason = u'Access denied'
            flash(u"Login failed: {}".format(reason), u'error')
            return redirect(url_for('login.login'))
        # Check CSRF token
        csrf_token = request.args['state']
        if not csrf.validate_csrf(csrf_token, time_limit=True):
            flash(u"CSRF validation failed. Please try logging in again.",
                    u'error')
            return redirect(url_for('login.login'))
        token = {'access_token': resp['access_token']}
        # Get the User object for this user, creating one if needed
        user = self.get_user(token)
        if user is not None:
            # Apply site-wide admin flag
            user.admin = self.is_admin(user)
            # Login the user, so current_user will work
            self.login_user(user)
        else:
            flash(u"Login failed.", u'error')
            return redirect(url_for('login.login'))
        # Add new Pilots
        current_pilots = self.get_pilots(token)
        for pilot in current_pilots:
            pilot.user = user
        # Remove old pilots
        user_pilots = set(user.pilots)
        for pilot in user_pilots:
            if pilot not in current_pilots:
                pilot.user = None
        db.session.commit()
        # Add new groups
        current_groups = self.get_groups(token)
        for group in current_groups:
            user.groups.add(group)
        # Remove old groups
        user_groups = set(user.groups)
        for group in user_groups:
            if group not in current_groups and group in user.groups:
                user.groups.remove(group)
        # Save all changes
        db.session.commit()
        return redirect(url_for('index'))

    def get_user(self, token):
        """Returns the :py:class:`~.OAuthUser` instance for the given token.

        This method is to be implemented by subclasses of
        :py:class:`OAuthMethod` to use whatever APIs they have access to to get
        the user account given an access token.

        :param token: The access token used for communicating with whatever API
            you're using.
        :type token: typically a :py:class:`dict` with the `access_token` key's
            value set to the token string.
        :rtype: :py:class:`OAuthUser`
        """
        raise NotImplementedError

    def is_admin(self, user):
        """Returns wether this user should be treated as a site-wide
        administrator.

        The default implementation checks if the user's name is contained
        within the list of administrators supplied as an argument to
        :py:class:`OAuthMethod`\.

        :param user: The user to check.
        :type user: :py:class:`~.OAuthUser`
        :rtype: bool
        """
        return user.name in self.admins

    def get_pilots(self, token):
        """Return a :py:class:`list` of :py:class:`~.Pilot`\s for the given
        token.

        Like :py:meth:`get_user`\, this method is to be implemented by
        :py:class:`OAuthMethod` subclasses to return a list of
        :py:class:`~.Pilot`\s associated with the account for the given access
        token.

        :param token: The access token used for communicating with whatever API
            you're using.
        :type token: typically a :py:class:`dict` with the `access_token` key's
            value set to the token string.
        :rtype: :py:class:`list` of :py:class:`~.Pilot`\s.
        """
        raise NotImplementedError

    def get_groups(self, token):
        """Returns a :py:class:`list` of :py:class:`~.Group`\s for the given
        token.

        Like :py:meth:`get_user` and :py:meth:`get_pilots`\, this method is to
        be implemented by :py:class:`OAuthMethod` subclasses to return a list
        of :py:class:`~.Group`\s associated with the account for the given
        access token.

        :param token: The access token used for communicating with whatever API
            you're using.
        :type token: typically a :py:class:`dict` with the `access_token` key's
            value set to the token string.
        :rtype: :py:class:`list` of :py:class:`~.Group`\s.
        """
        raise NotImplementedError


class OAuthUser(User):
    id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True)
    token = db.Column(db.String(100, convert_unicode=True))
