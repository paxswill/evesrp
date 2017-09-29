from __future__ import absolute_import
from collections import defaultdict
import datetime as dt
import time
from decimal import Decimal
from functools import partial
import re
import sys
import six
from .util import unistr, urlparse, urlunparse, utc

from flask import Markup, current_app
from flask_babel import gettext, lazy_gettext
import iso8601
import requests
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.sql import select

from . import ships, systems


if six.PY3:
    unicode = str


@unistr
class Killmail(object):
    """Base killmail representation.

    .. py:attribute:: kill_id

        The ID integer of this killmail. Used by most killboards and by CCP to
        refer to killmails.

    .. py:attribute:: ship_id

        The typeID integer of for the ship lost for this killmail.

    .. py:attribute:: ship

        The human readable name of the ship lost for this killmail.

    .. py:attribute:: pilot_id

        The ID number of the pilot who lost the ship. Referred to by CCP as
        ``characterID``.

    .. py:attribute:: pilot

        The name of the pilot who lost the ship.

    .. py:attribute:: corp_id

        The ID number of the corporation :py:attr:`pilot` belonged to at the
        time this kill happened.

    .. py:attribute:: corp

        The name of the corporation referred to by :py:attr:`corp_id`.

    .. py:attribute:: alliance_id

        The ID number of the alliance :py:attr:`corp` belonged to at the time
        of this kill, or ``None`` if the corporation wasn't in an alliance at
        the time.

    .. py:attribute:: alliance

        The name of the alliance referred to by :py:attr:`alliance_id`.

    .. py:attribute:: url

        A URL for viewing this killmail's information later. Typically an
        online killboard such as `zKillboard <https://zkillboard.com>`_, but
        other kinds of links may be used.

    .. py:attribute:: value

        The extimated ISK loss for the ship destroyed in this killmail. This is
        an optional attribute, and is ``None`` if unsupported. If this
        attribute is set, it should be a :py:class:`~.Decimal` or at least a
        type that can be used as the value for the :py:class:`~.Decimal`
        constructor.

    .. py:attribute:: timestamp

        The date and time that this kill occured as a
        :py:class:`datetime.datetime` object (with a UTC timezone).

    .. py:attribute:: verified

        Whether or not this killmail has been API verified (or more accurately,
        if it is to be trusted when making a
        :py:class:`~evesrp.models.Request`.

    .. py:attribute:: system

        The name of the system where the kill occured.

    .. py:attribute:: system_id

        The ID of the system where the kill occured.

    .. py:attribute:: constellation

        The name of the constellation where the kill occured.

    .. py:attribute:: region

        The name of the region where the kill occured.
    """

    def __init__(self, **kwargs):
        """Initialize a :py:class:`Killmail` with ``None`` for all attributes.

        All subclasses of this class, (and all mixins designed to be used with
        it) must call ``super().__init__(**kwargs)`` to ensure all
        initialization is done.

        :param: keyword arguments corresponding to attributes.
        """
        self._data = defaultdict(lambda: None)
        for attr in ('kill_id', 'ship_id', 'ship', 'pilot_id', 'pilot',
                     'corp_id', 'corp', 'alliance_id', 'alliance', 'verified',
                     'url', 'value', 'timestamp', 'system', 'constellation',
                     'region', 'system_id'):
            try:
                setattr(self, attr, kwargs[attr])
            except KeyError:
                pass
            else:
                del kwargs[attr]
        super(Killmail, self).__init__(**kwargs)

    # Any attribute not starting with an underscore will be stored in a
    # separate, private attribute. This is to allow attributes on Killmail to
    # be redfined as a property.

    def __getattr__(self, name):
        try:
            return self._data[name]
        except KeyError as e:
            raise AttributeError(unicode(e))

    def __setattr__(self, name, value):
        if name[0] == '_':
            object.__setattr__(self, name, value)
        else:
            self._data[name] = value

    def __unicode__(self):
        # TRANS: This is a very brief desription of the unique, pertinent
        # information about a killmail.
        return gettext(u"%(kill_id)d: %(pilot)s lost a ship. Verified: "
                       u"%(verified)s",
                kill_id=self.kill_id,
                pilot=self.pilot,
                ship=self.ship,
                verified=self.verified)

    def __iter__(self):
        """Iterate over the attributes of this killmail.

        Yields tuples in the form ``('<name>', <value>)``. This is used by
        :py:meth:`Request.__init__ <evesrp.models.Request.__init__>` to
        initialize its data quickly. ``<name>`` in the returned tuples is the
        name of the attribute on the :py:class:`~evesrp.models.Request`.
        """
        yield ('id', self.kill_id)
        yield ('ship_type', self.ship)
        yield ('corporation', self.corp)
        yield ('alliance', self.alliance)
        yield ('killmail_url', self.url)
        yield ('base_payout', self.value)
        yield ('kill_timestamp', self.timestamp)
        yield ('system', self.system)
        yield ('constellation', self.constellation)
        yield ('region', self.region)
        yield ('pilot_id', self.pilot_id)


    # TRANS: This is a description of the killmail processor. This specific
    # text should not be shown to the user, but should still be localized just
    # in case.
    description = lazy_gettext(u"A generic Killmail. If you see this text, you"
                               u" need to configure your application.")
    """A user-facing description of what kind of killmails this
    :py:class:`Killmail` validates/handles. This text is displayed below
    the text field for a killmail URL to let users know what kinds of links
    are acceptable.
    """


class ShipNameMixin(object):
    """Killmail mixin providing :py:attr:`Killmail.ship` from
    :py:attr:`Killmail.ship_id`.
    """

    @property
    def ship(self):
        """Looks up the ship name using :py:attr:`Killmail.ship_id`.
        """
        return ships.ships[self.ship_id]


class LocationMixin(object):
    """Killmail mixin for providing solar system, constellation and region
    names from :py:attr:`Killmail.system_id`.
    """

    @property
    def system(self):
        """Provides the solar system name using :py:attr:`Killmail.system_id`.
        """
        return systems.system_names[self.system_id]

    @property
    def constellation(self):
        """Provides the constellation name using :py:attr:`Killmail.system_id`.
        """
        constellation_id = systems.systems_constellations[self.system_id]
        return systems.constellation_names[constellation_id]

    @property
    def region(self):
        """Provides the region name using :py:attr:`Killmail.system_id`.
        """
        constellation_id = systems.systems_constellations[self.system_id]
        region_id = systems.constellations_regions[constellation_id]
        return systems.region_names[region_id]


class RequestsSessionMixin(object):
    """Mixin for providing a :py:class:`requests.Session`.

    The shared session allows HTTP user agents to be set properly, and for
    possible connection pooling.

    .. py:attribute:: requests_session

        A :py:class:`~requests.Session` for making HTTP requests.
    """
    def __init__(self, requests_session=None, **kwargs):
        """Set up a :py:class:`~requests.Session` for making HTTP requests.

        If an existing session is not provided, one will be created.

        :param requests_session: an existing session to use.
        :type requests: :py:class:`~requests.Session`
        """
        if requests_session is None:
            try:
                self.requests_session = current_app.requests_session
            except (AttributeError, RuntimeError):
                self.requests_session = requests.Session()
        else:
            self.requests_session = requests_session
        super(RequestsSessionMixin, self).__init__(**kwargs)


class ZKillmail(Killmail, RequestsSessionMixin, ShipNameMixin, LocationMixin):
    """A killmail sourced from a zKillboard based killboard."""

    zkb_regex = re.compile(r'/(detail|kill)/(?P<kill_id>\d+)/?')

    def __init__(self, url, **kwargs):
        """Create a killmail from the given zKillboard URL.

        :param str url: The URL of the killmail.
        :raises ValueError: if ``url`` isn't a valid zKillboard killmail.
        :raises LookupError: if the zKillboard API response is in an unexpected
            format.
        """
        super(ZKillmail, self).__init__(**kwargs)
        self.url = url
        match = self.zkb_regex.search(url)
        if match:
            self.kill_id = int(match.group('kill_id'))
        else:
            # TRANS: Error message shown when an invalid zKillboard URL is
            # entered.
            raise ValueError(gettext(u"'%(url)s' is not a valid zKillboard "
                                     u"killmail", url=self.url))
        parsed = urlparse(self.url, scheme='https')
        if parsed.netloc == '':
            # Just in case someone is silly and gives an address without a
            # scheme. Also fix self.url to have a scheme.
            parsed = urlparse('//' + url, scheme='https')
            self.url = parsed.geturl()
        self.domain = parsed.netloc
        # Check API
        api_url = [a for a in parsed]
        api_url[2] = '/api/no-attackers/no-items/killID/{}/'.format(
                self.kill_id)
        resp = self.requests_session.get(urlunparse(api_url))
        # TRANS: Error message shown when there's a problem accessing the
        # zKillboard API.
        retrieval_error = LookupError(gettext(u"Error retrieving killmail "
                                              u"data: %(code)d",
                                              code=resp.status_code))
        if resp.status_code != 200:
            raise retrieval_error
        try:
            json = resp.json(parse_float=Decimal)
        except ValueError as e:
            raise retrieval_error
        try:
            json = json[0]
        except IndexError as e:
            # TRANS: This is an error message when the killmail is somehow
            # failing to be recognized. The %(url)s is replaced with the URL of
            # the offending killmail.
            raise LookupError(gettext(u"Invalid killmail: %(url)s", url=url))
        # JSON is defined to be UTF-8 in the standard
        victim = json[u'victim']
        self.pilot_id = int(victim[u'characterID'])
        self.pilot = victim[u'characterName']
        self.corp_id = int(victim[u'corporationID'])
        self.corp = victim[u'corporationName']
        if victim[u'allianceID'] != '0':
            self.alliance_id = int(victim[u'allianceID'])
            self.alliance = victim[u'allianceName']
        self.ship_id = int(victim[u'shipTypeID'])
        self.system_id = int(json[u'solarSystemID'])
        # For consistency, store self.value in millions. Decimal is being used
        # for precision at large values.
        # Old versions of zKB don't give the ISK value
        self.value = json[u'zkb'].get(u'totalValue', Decimal(0))
        # Old versions of zKB return numerical values as strings.
        if not isinstance(self.value, Decimal):
            self.value = Decimal(self.value)
        # Parse the timestamp
        time_struct = time.strptime(json[u'killTime'], '%Y-%m-%d %H:%M:%S')
        self.timestamp = dt.datetime(*(time_struct[0:6]),
                tzinfo=utc)

    @property
    def verified(self):
        # zKillboard assigns unverified IDs negative numbers
        return self.kill_id > 0

    def __unicode__(self):
        # TRANS: A quick summary of a killmail's pertinent information.
        return gettext(u"%(kill_id)d: %(pilot)s lost a ship. Verified: "
                       u"%(verified)s. ZKillboard URL: %(url).",
                kill_id=self.kill_id,
                pilot=self.pilot,
                ship=self.ship,
                verified=self.verified,
                url=self.url)


    # TRANS: Decscribing the acceptable killmails for the ZKillboard killmail
    # processor.
    description = lazy_gettext(u'A link to a lossmail from <a '
                                      u'href="https://zkillboard.com/">'
                                      u'ZKillboard</a>.')


class ESIMail(Killmail, RequestsSessionMixin, LocationMixin):
    """A killmail with data sourced from a ESI killmail link."""

    esi_regex = re.compile(r'/v1/killmails/(?P<kill_id>\d+)/[0-9a-f]+/')

    @staticmethod
    def _raise_esi_lookup(esi_error):
        # TRANS: The %s here will be replaced with the (non-localized
        # probably) error from CCP.
        raise LookupError(gettext(u"Error retrieving ESI killmail: "
                                  u"%(error)s",
                                  error=esi_error))

    def __init__(self, url, **kwargs):
        """Create a killmail from a ESI killmail link.

        :param str url: the ESI killmail URL.
        :raises ValueError: if ``url`` is not a ESI URL.
        :raises LookupError: if the ESI API response is in an unexpected
            format.
        """
        super(ESIMail, self).__init__(**kwargs)
        self.url = url
        match = self.esi_regex.search(self.url)
        if match:
            self.kill_id = match.group('kill_id')
        else:
            # TRANS: The %(url)s in this case will be replaced with the
            # offending URL.
            raise ValueError(gettext(u"'%(url)s' is not a valid ESI killmail",
                    url=self.url))
        parsed = urlparse(self.url, scheme='https')
        if parsed.netloc == '':
            parsed = urlparse('//' + url, scheme='https')
            self.url = parsed.geturl()
        # Check if it's a valid ESI URL
        resp = self.requests_session.get(self.url)
        # JSON responses are defined to be UTF-8 encoded
        # TODO handle all the documented error codes form CCP
        if resp.status_code != 200:
            self._raise_esi_lookup(resp.json()[u'message'])
        try:
            json = resp.json()
        except ValueError as e:
            # TRANS: The %(code)d in this message will be replaced with the
            # HTTP status code recieved from CCP.
            raise LookupError(gettext(u"Error retrieving killmail data: "
                                      u"%(code)d", code=resp.status_code))
        victim = json[u'victim']
        self.pilot_id = victim[u'character_id']
        self.corp_id = victim[u'corporation_id']
        self.alliance_id = victim.get(u'alliance_id')
        self.ship_id = victim[u'ship_type_id']
        self.system_id = json[u'solar_system_id']
        self.timestamp = iso8601.parse_date(json[u'killmail_time'])
        # Look up the names of the *_id attributes above. Doing this in here
        # instead of making a mixin because /universe/names lets us cut down on
        # the number of requests we have to make.
        ids = [self.ship_id, self.system_id]
        # /universe/names/ doesn't look up character/corporation/alliance IDs
        # in the range 100000000 between 2099999999. The devblog isn't clear if
        # this is inclusive, so let's err on the side of caution. Instead, we
        # have to look up those IDs individually.
        special_ids = ['pilot_id', 'corp_id']
        if self.alliance_id != 0:
            # Handle corporations not in alliances
            special_ids.append('alliance_id')
        for id_attr in special_ids:
            id_value = getattr(self, id_attr)
            if 100000000 <= id_value <= 2099999999:
                esi_urls = {
                    'pilot_id': 'https://esi.tech.ccp.is/v4/characters/{}/',
                    'corp_id': 'https://esi.tech.ccp.is/v3/corporations/{}/',
                    'alliance_id': 'https://esi.tech.ccp.is/v2/alliances/{}/',
                }
                special_resp = self.requests_session.get(
                    esi_urls[id_attr].format(id_value))
                if special_resp.status_code != 200:
                    self._raise_esi_lookup(special_resp.json()['error'])
                # CCP uses different names for the 'name' attribute
                name_attrs = {
                    'pilot_id': u'name',
                    'corp_id': u'corporation_name',
                    'alliance_id': u'alliance_name',
                }
                name = special_resp.json()[name_attrs[id_attr]]
                setattr(self, id_attr[:-3], name)
            else:
                ids.append(id_value)
        names_resp = self.requests_session.post(
            'https://esi.tech.ccp.is/v2/universe/names/', json=ids)
        if names_resp.status_code != 200:
            self._raise_esi_lookup(names_resp.json()[u'error'])
        for name_info in names_resp.json():
            category_attributes = {
                'solar_system': 'system',
                'inventory_type': 'ship',
                'character': 'pilot',
                'alliance': 'alliance',
                'corporation': 'corporation',
            }
            attr_name = category_attributes[name_info[u'category']]
            name = name_info[u'name']
            setattr(self, attr_name, name)
        # ESI Killmails are always verified
        self.verified = True

    # TRANS: Description of the allowable links for the ESI killmail
    # processor.
    description = lazy_gettext(u'An ESI external killmail link.')


# Backwards compatibility
CRESTMail = ESIMail
