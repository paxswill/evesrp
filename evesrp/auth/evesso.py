from __future__ import absolute_import

import xml.etree.ElementTree as ET
from flask import request, current_app, abort, flash
from sqlalchemy.orm.exc import NoResultFound
from flask.ext.wtf import Form

from .oauth import OAuthMethod, OAuthUser
from .. import db
from .models import Group, Pilot
from ..util.fields import ImageField
from ..versioned_static import static_file


CREST_CONTENT_TYPE = 'application/vnd.ccp.eve.Api-v3+json; charset=utf-8'


def check_crest_response(response):
    """Check for CREST representation deprecation/removal.

    Specifically, check that the status code isn't 406 (meaning the
    representation has been removed) and for the presence of the X-Deprecated
    header.

    :param Response response: A :py:class:`~.Response` to check.
    :rtype: bool
    """
    # TODO Add a test case for this
    if response.status_code == 406:
        flash((u"This version of EVE SRP no longer knows how to interface with"
               u"the CREST API. Please update to the latest version."),
               u'error')
        return False
    if 'X-Deprecated' in response.headers:
        flash((u"The version of the CREST representation known by EVE SRP "
               u"has been deprecated. Please update to the latest version "
               u"to ensure continued operation."), u'warn')
    return True


class EveSSO(OAuthMethod):

    def __init__(self, singularity=False, **kwargs):
        # CREST URLs are all specified as absolute URLs, so skip setting a base
        # URL
        kwargs.setdefault('base_url', u'')
        # Set a member for the crest URLs
        if not singularity:
            self.root_urls = {
                'public': 'https://public-crest.eveonline.com/',
                'authed': 'https://crest-tq.eveonline.com/',
            }
            self.xml_root = 'https://api.eveonline.com/'
        else:
            self.root_urls = {
                'public': 'http://public-crest-sisi.testeveonline.com/',
                'authed': 'https://api-sisi.testeveonline.com/',
            }
            self.xml_root = 'https://api.testeveonline.com/'
        # Discover the OAuth endpoints by looking in the CREST root
        public_resp = current_app.requests_session.get(
                self.root_urls['public'],
                headers={'Accept': CREST_CONTENT_TYPE})
        check_crest_response(public_resp)
        public_root = public_resp.json()
        crest_token_url = public_root[u'authEndpoint'][u'href']
        kwargs.setdefault('access_token_url', crest_token_url)
        kwargs.setdefault('authorize_url',
                crest_token_url.replace('token', 'authorize'))

        kwargs.setdefault('access_token_method', 'POST')
        kwargs.setdefault('content_type', 'application/json')
        kwargs.setdefault('app_key', 'EVE_SSO')
        kwargs.setdefault('name', u'EVE SSO')
        super(EveSSO, self).__init__(**kwargs)

    def _get_user_data(self, token):
        if not hasattr(request, '_user_data'):
            # Get the public CREST root to infer where the verification
            # endpoint is
            public_resp = current_app.requests_session.get(
                    self.root_urls['public'],
                    headers={'Accept': CREST_CONTENT_TYPE} )
            check_crest_response(public_resp)
            public_root = public_resp.json()
            verify_url = public_root[u'authEndpoint'][u'href'].replace(
                    'token', 'verify')
            # TODO Add CREST headers and response verification for the OAuth
            # methods.
            resp = self.oauth.get(verify_url, token=token)
            current_app.logger.debug(u"SSO lookup results: {}".format(
                    resp.data))
            try:
                char_data = {
                    'name': resp.data[u'CharacterName'],
                    'id': resp.data[u'CharacterID'],
                    'owner_hash': resp.data[u'CharacterOwnerHash'],
                }
                request._user_data = char_data
            except (TypeError, KeyError):
                abort(500, u"Error in receiving EVE SSO response: {}".format(
                        resp.data))
        return request._user_data

    def form(self):
        class EveSSOForm(Form):
            submit = ImageField(src=static_file('evesso.png'),
                    alt=u"Log in with EVE Online")

        return EveSSOForm

    def get_user(self, token):
        character = self._get_user_data(token)
        try:
            user = EveSSOUser.query.filter_by(
                    owner_hash=character['owner_hash'],
                    authmethod=self.name).one()
        except NoResultFound:
            user = EveSSOUser(
                    character['name'],
                    character['owner_hash'],
                    self.name,
                    token=token['access_token'])
            db.session.add(user)
            db.session.commit()
        return user

    def get_pilots(self, token):
        # The EVE SSO API only authenticates one character at a time, so we're
        # going to have a 1-to-1 mapping of Users to Pilots
        character = self._get_user_data(token)
        pilot = Pilot.query.get(int(character['id']))
        if pilot is None:
            pilot = Pilot(None, character['name'], character['id'])
            db.session.add(pilot)
            db.session.commit()
        return [pilot]

    def get_groups(self, token):
        """Set the user's groups for their pilot.

        At this time, Eve SSO only gives us character access, so they're just
        set to the pilot's corporation, and if they have on their alliance as
        well. In the future, this method may also add groups for mailing lists.
        """
        character = self._get_user_data(token)
        info_url = self.xml_root + 'eve/CharacterInfo.xml.aspx'
        info_response = current_app.requests_session.get(info_url,
                params={'characterID': character['id']})
        api_tree = ET.fromstring(info_response.text).find('result')
        corp_name = api_tree.find('corporation')
        corp_id = api_tree.find('corporationID')
        corporation = {
            'name': corp_name.text,
            'id': int(corp_id.text),
        }
        try:
            corp_group = EveSSOGroup.query.filter_by(alliance=False,
                    ccp_id=int(corp_id.text),
                    authmethod=self.name).one()
        except NoResultFound:
            corp_group = EveSSOGroup(corp_name.text, int(corp_id.text), False,
                    self.name)
            db.session.add(corp_group)
        groups = [corp_group]

        alliance_name = api_tree.find('alliance')
        alliance_id = api_tree.find('allianceID')
        # If there's an alliance, set it up
        if alliance_name is not None and alliance_id is not None:
            try:
                alliance_group = EveSSOGroup.query.filter_by(alliance=True,
                        ccp_id=int(alliance_id.text),
                        authmethod=self.name).one()
            except NoResultFound:
                alliance_group = EveSSOGroup(alliance_name.text,
                        int(alliance_id.text), True, self.name)
                db.session.add(alliance_group)
        db.session.commit()
        return groups


class EveSSOUser(OAuthUser):

    id = db.Column(db.Integer, db.ForeignKey(OAuthUser.id), primary_key=True)

    owner_hash = db.Column(db.String(50), nullable=False, unique=True,
            index=True)

    def __init__(self, username, owner_hash, authmethod, groups=None, **kwargs):
        self.owner_hash = owner_hash
        super(EveSSOUser, self).__init__(username, authmethod, **kwargs)


class EveSSOGroup(Group):

    id = db.Column(db.Integer, db.ForeignKey(Group.id), primary_key=True)

    ccp_id = db.Column(db.Integer, nullable=False, unique=True, index=True)

    alliance = db.Column(db.Boolean, nullable=False, default=False,
            index=True)

    __table_args__ = (
            db.UniqueConstraint(ccp_id, alliance),
    )

    def __init__(self, name, ccp_id, alliance, authmethod, **kwargs):
        self.ccp_id = ccp_id
        self.alliance = alliance
        super(EveSSOGroup, self).__init__(name, authmethod, **kwargs)
