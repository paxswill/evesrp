from __future__ import absolute_import
import datetime as dt
from flask import flash, redirect, current_app, url_for, request, session
from flask_babel import gettext
from flask_login import current_user, login_user, login_fresh
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import OAuth2Error
from flask_wtf import csrf
import six
from sqlalchemy.orm.exc import NoResultFound

from .. import db, sentry
from ..util import ensure_unicode, DateTime, is_safe_redirect
from . import AuthMethod
from .models import User, Group, Pilot


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

        * ``client_id``
        * ``client_secret``
        * ``scope``
        * ``access_token_url``
        * ``refresh_token_url``
        * ``authorize_url``
        * ``access_token_params``
        * ``method``

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

        :param default_token_expiry: The default time (in seconds) access
            tokens are valid for. Defaults to 5 minutes.
        :type default_token_expiry: :py:class:`int`
        """
        keyword_mapping = {
            'key': 'client_id',
            'consumer_key': 'client_id',
            'secret': 'client_secret',
            'consumer_secret': 'client_secret',
            'access_token_method': 'method',
        }
        for old_kw, new_kw in six.iteritems(keyword_mapping):
            if old_kw in kwargs:
                # TODO: Raise a deprecation warning
                kwargs[new_kw] = kwargs.pop(old_kw)
        # TODO: add handling for old request_token_params and pulling scope out?
        # Save arguments used for later operations
        self.client_id = kwargs.pop('client_id')
        self.client_secret = kwargs.pop('client_secret')
        self.authorize_url = kwargs.pop('authorize_url')
        self.token_url = kwargs.pop('access_token_url')
        self.refresh_url = kwargs.pop('refresh_token_url', None)
        self.oauth_method = kwargs.pop('method', 'POST')
        self.scope = kwargs.pop('scope', None)
        self.default_token_expiry = kwargs.pop('default_token_expiry', 300)
        self.name = kwargs.get('name', 'OAuth')
        try:
            self.access_params = kwargs.pop('access_token_params')
        except KeyError:
            self.access_params = {}

        # Small function that will mark users as stale (not fresh) for
        # Flask-Login if they no longer have valid tokens. This will trigger a
        # refresh if there are refresh tokens, or require them to login on the
        # next attempted privileged action.
        @current_app.before_request
        def enforce_user_freshness():
            if current_user.is_authenticated and \
                    current_user.authmethod == self.name and \
                    login_fresh():
                user = current_user._get_current_object()
                if user.seconds_valid <= 0:
                    current_app.logger.debug("Marking '{}' as stale".format(
                        user))
                    login_user(user, fresh=False)
                    self.session.token = user.token

        super(OAuthMethod, self).__init__(**kwargs)

    # Being done in a property so when url_for is called, it has access to a
    # request, specifically the scheme.
    @property
    def redirect_uri(self):
        return  url_for('login.auth_method_login',
                auth_method=self.safe_name, _external=True)


    def login(self, form):
        oauth = OAuth2Session(self.client_id,
                redirect_uri=self.redirect_uri,
                scope=self.scope)
        url, state = oauth.authorization_url(self.authorize_url)
        session['state'] = state
        current_app.logger.debug(u"Redirecting to : {}".format(url))
        # Stash the 'next' parameter in the session to use it in the 'view'
        # view. It's automatically added by Flask-Login.
        if 'next' in request.args:
            session['next'] = request.args['next']
        return redirect(url)

    def view(self):
        """Handle creating and/or logging in the user and updating their
        :py:class:`~.Pilot`\s and :py:class:`~.Group`\s.
        """
        oauth = OAuth2Session(self.client_id,
                redirect_uri=self.redirect_uri,
                state=session['state'])
        try:
            token = oauth.fetch_token(self.token_url,
                    authorization_response=request.url,
                    method=self.oauth_method,
                    client_secret=self.client_secret,
                    auth=(self.client_id, self.client_secret))
        except OAuth2Error as e:
            # TRANS: When there's an error associated with a login.
            flash(gettext(u"Login failed: %(error)s", error=e.error))
            if 'SENTRY_RELEASE' in current_app.config:
                sentry.captureException()
            return redirect(url_for('login.login'))
        # Set the current session manually because the automated method relies
        # on current_user.
        self.session = OAuth2Session(self.client_id, token=token)
        # Get the User object for this user, creating one if needed
        user = self.get_user()
        # Update the tokens (and related info) for the user
        user.access_token = token[u'access_token']
        # If not given by the server, use the default expiry time
        if u'expires_in' in token:
            user.set_expiration(token[u'expires_in'])
        else:
            user.set_expiration(self.default_token_expiry)
        user.refresh_token = token.get(u'refresh_token')
        db.session.commit()
        if user is not None:
            # Login the user, so current_user will work
            self.login_user(user)
        else:
            # TRANS: Error shown for a failed login.
            flash(gettext(u"Login failed."), u'error')
            return redirect(url_for('login.login'))
        # Update admins, groups and pilots for the current user
        self._update_user_info()
        # Redirect to the 'next' parameter given to the 'login' view.
        # The next parameter is automatically added by Flask-Login.
        # Check that the 'next' parameter is safe.
        next_url = request.args.get('next')
        if next_url is not None:
            if not is_safe_redirect(next_url):
                next_url = None
        return redirect(next_url or url_for('index'))


    def _update_user_info(self):
        current_app.logger.debug(
                "Updating information for '{}' with OAuth".format(current_user))
        # Set the site-wide admin flag
        current_user.admin = self.is_admin(current_user)
        # Add new Pilots
        current_pilots = self.get_pilots()
        for pilot in current_pilots:
            pilot.user = current_user
        # Remove old pilots
        user_pilots = set(current_user.pilots)
        for pilot in user_pilots:
            if pilot not in current_pilots:
                pilot.user = None
        # Add new groups
        current_groups = self.get_groups()
        for group in current_groups:
            current_user.groups.add(group)
        # Remove old groups
        user_groups = set(current_user.groups)
        for group in user_groups:
            if group not in current_groups and group in current_user.groups:
                current_user.groups.remove(group)
        # Save all changes
        db.session.commit()

    def get_user(self):
        """Returns the :py:class:`~.OAuthUser` instance for the current token.

        This method is to be implemented by subclasses of
        :py:class:`OAuthMethod` to use whatever APIs they have access to to get
        the user account given an access token.

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

    def get_pilots(self):
        """Return a :py:class:`list` of :py:class:`~.Pilot`\s for the given
        token.

        Like :py:meth:`get_user`\, this method is to be implemented by
        :py:class:`OAuthMethod` subclasses to return a list of
        :py:class:`~.Pilot`\s associated with the account for the given access
        token.

        :rtype: :py:class:`list` of :py:class:`~.Pilot`\s.
        """
        raise NotImplementedError

    def get_groups(self):
        """Returns a :py:class:`list` of :py:class:`~.Group`\s for the given
        token.

        Like :py:meth:`get_user` and :py:meth:`get_pilots`\, this method is to
        be implemented by :py:class:`OAuthMethod` subclasses to return a list
        of :py:class:`~.Group`\s associated with the account for the given
        access token.

        :rtype: :py:class:`list` of :py:class:`~.Group`\s.
        """
        raise NotImplementedError

    def refresh(self, user):
        """Refreshes the current user's information.

        Attempts to refresh the pilots and groups for the given user. If the
        current access token has expired, the refresh token is used to get a
        new access token.
        """
        try:
            self._update_user_info()
        except OAuth2Error:
            return False
        else:
            return True

    @property
    def session(self):
        if not hasattr(self, '_oauth_session'):
            if not current_user.is_anonymous:
                kwargs = {
                    'token': current_user.token,
                }
                if self.refresh_url is not None:
                    kwargs['auto_refresh_url'] = self.refresh_url
                    kwargs['token_updater'] = token_saver
                    kwargs['auto_refresh_kwargs'] = {
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                    }
                current_app.logger.debug(u"Creating a new OAuth2Session for "
                                         u"'{}'".format(current_user))
                self._oauth_session = OAuth2Session(self.client_id, **kwargs)
        return self._oauth_session

    @session.setter
    def session(self, new_session):
        self._oauth_session = new_session

    @session.deleter
    def session(self):
        del self._oauth_session


def token_saver(token):
    current_app.logger.debug("Saving new OAuth tokens for user '{}'".format(
        current_user))
    current_user.access_token = token[u'access_token']
    refresh_token = token.get(u'refresh_token')
    if refresh_token is not None and \
            refresh_token == current_user.refresh_token:
        current_app.logger.warning(u"Refresh token did not change.")
    else:
        current_user.refresh_token = refresh_token
    current_user.set_expiration(token.get(u'expires_in', 0))
    db.session.commit()


class OAuthUser(User):

    id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True)

    access_token = db.Column(db.String(100, convert_unicode=True))

    access_expiration = db.Column(DateTime, default=None)

    refresh_token = db.Column(db.String(100, convert_unicode=True))

    def set_expiration(self, expiration_seconds):
        now = dt.datetime.utcnow()
        expiration = now + dt.timedelta(seconds=expiration_seconds)
        self.access_expiration = expiration

    @property
    def seconds_valid(self):
        if self.access_expiration is not None:
            now = dt.datetime.utcnow()
            current_duration = self.access_expiration - now
            return current_duration.total_seconds()
        else:
            return 0

    @property
    def token(self):
        token = {'token_type': 'Bearer'}
        token['access_token'] = self.access_token
        token['expires_in'] = int(self.seconds_valid)
        if self.refresh_token is not None:
            token['refresh_token'] = self.refresh_token
        return token
