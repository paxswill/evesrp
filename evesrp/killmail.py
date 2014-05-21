from collections import defaultdict
import datetime as dt
import time
from decimal import Decimal
from functools import partial
import re
import sys
from urllib.parse import urlparse, urlunparse, quote

import requests
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.sql import select

from . import ships, systems


class Killmail(object):
    """Base killmail representation.

    .. py:attribute:: kill_id

        The ID integer of this killmail. Used by most killboards and by CCP to
        refer to killmails.

    .. py:attribute:: ship_id

        The typeID integer of for the ship lost for this killmail.

    .. py:attribute:: ship

        The human readable name of the ship lost for this killmail.

    .. py:attribute:: ship_url

        This is an optional atribute for subclasses to implement. It's intended
        to be used for requests to link to a custom, possibly external,
        ship-specific page.

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
        online killboard such as `zKillboard <https://zkillboard.com>`, but
        other kinds of links may be used.

    .. py:attribute:: value

        The extimated ISK loss for the ship destroyed in this killmail. This is
        an optional attribute, and is ``None`` if unsupported. If this
        attribute is set, it should be a floating point number (or something
        like it, like :py:class:`decimal.Decimal`) representing millions of
        ISK.

    .. py:attribute:: timestamp

        The date and time that this kill occured as a
        :py:class:`datetime.datetime` object (with a UTC timezone).

    .. py:attribute:: verified

        Whether or not this killmail has been API verified (or more accurately,
        if it is to be trusted when making a
        :py:class:`~evesrp.models.Request`.

    .. py:attribute:: system
    .. py:attribute:: system_id
    .. py:attribute:: constellation
    .. py:attribute:: region

        The system/constellation/region where the kill occured.
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

    # Any attribute not starting with an underscore will now be stored in a
    # separate, private attribute. This is to allow attribute on Killmail to be
    # redfined as a property.

    def __getattr__(self, name):
        try:
            return self._data[name]
        except KeyError as e:
            raise AttributeError from e

    def __setattr__(self, name, value):
        if name[0] == '_':
            object.__setattr__(self, name, value)
        else:
            self._data[name] = value

    def __str__(self):
        return "{kill_id}: {pilot} lost a {ship}. Verified: {verified}.".\
                format(kill_id=self.kill_id, pilot=self.pilot, ship=self.ship,
                        verified=self.verified)

    def __iter__(self):
        """Iterate over the attributes of this killmail.

        Yields tuples in the form ``('<name>', <value>)``. This is used by
        :py:meth:`evesrp.models.Request.__init__` to initialize its data
        quickly. The `<name>` in the returned tuples is the name of the
        attribute on the :py:class:`~evesrp.models.Request`.
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
        return systems.systems_constellations[self.system]

    @property
    def region(self):
        """Provides the region name using :py:attr:`Killmail.system_id`.
        """
        return systems.constellations_regions[self.constellation]


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
            self.requests_session = requests.Session()
        else:
            self.requests_session = requests_session
        super(RequestsSessionMixin, self).__init__(**kwargs)


class ZKillmail(Killmail, RequestsSessionMixin, ShipNameMixin, LocationMixin):
    """A killmail sourced from a zKillboard based killboard."""

    zkb_regex = re.compile(r'/(detail|kill)/(?P<kill_id>\d+)/?')

    def __init__(self, url, **kwargs):
        """Create a killmail from the given URL.

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
            raise ValueError("'{}' is not a valid zKillboard killmail".
                    format(self.url))
        parsed = urlparse(self.url, scheme='https')
        if parsed.netloc == '':
            # Just in case someone is silly and gives an address without a
            # scheme. Also fix self.url to have a scheme.
            parsed = urlparse('//' + url, scheme='https')
            self.url = urlunparse(parsed)
        self.domain = parsed.netloc
        # Check API
        api_url = [a for a in parsed]
        api_url[2] = '/api/killID/{}'.format(self.kill_id)
        resp = self.requests_session.get(urlunparse(api_url))
        try:
            json = resp.json()[0]
        except ValueError as e:
            raise LookupError("Error retrieving killmail data: {}"
                    .format(resp.status_code)) from e
        victim = json['victim']
        self.pilot_id = int(victim['characterID'])
        self.pilot = victim['characterName']
        self.corp_id = int(victim['corporationID'])
        self.corp = victim['corporationName']
        if victim['allianceID'] != '0':
            self.alliance_id = int(victim['allianceID'])
            self.alliance = victim['allianceName']
        self.ship_id = int(victim['shipTypeID'])
        self.system_id = int(json['solarSystemID'])
        # For consistency, store self.value in millions. Decimal is being used
        # for precision at large values.
        # Old versions of zKB don't give the ISK value
        try:
            value = Decimal(json['zkb']['totalValue'])
        except KeyError:
            value = 0
        self.value = value / 1000000
        # Parse the timestamp
        time_struct = time.strptime(json['killTime'], '%Y-%m-%d %H:%M:%S')
        self.timestamp = dt.datetime(*(time_struct[0:6]),
                tzinfo=dt.timezone.utc)

    @property
    def verified(self):
        # zKillboard assigns unverified IDs negative numbers
        return self.kill_id > 0

    def __str__(self):
        parent = super(ZKillmail, self).__str__()
        return "{parent} From ZKillboard at {url}".format(parent=parent,
                url=self.url)


class CRESTMail(Killmail, RequestsSessionMixin, LocationMixin):
    """A killmail with data sourced from a CREST killmail link."""

    crest_regex = re.compile(r'/killmails/(?P<kill_id>\d+)/[0-9a-f]+/')

    def __init__(self, url, **kwargs):
        """Create a killmail from a CREST killmail link.

        :param str url: the CREST killmail URL.
        :raises ValueError: if ``url`` is not a CREST URL.
        :raises LookupError: if the CREST API response is in an unexpected
            format.
        """
        super(CRESTMail, self).__init__(**kwargs)
        self.url = url
        match = self.crest_regex.search(self.url)
        if match:
            self.kill_id = match.group('kill_id')
        else:
            raise ValueError("'{}' is not a valid CREST killmail".
                    format(self.url))
        parsed = urlparse(self.url, scheme='https')
        if parsed.netloc == '':
            parsed = urlparse('//' + url, scheme='https')
            self.url = urlunparse(parsed)
        # Check if it's a valid CREST URL
        resp = self.requests_session.get(self.url)
        try:
            json = resp.json()
        except ValueError as e:
            raise LookupError("Error retrieving killmail data: {}"
                    .format(resp.status_code)) from e
        victim = json['victim']
        char = victim['character']
        corp = victim['corporation']
        ship = victim['shipType']
        alliance = victim['alliance']
        self.pilot_id = char['id']
        self.pilot = char['name']
        self.corp_id = corp['id']
        self.corp = corp['name']
        self.alliance_id = alliance['id']
        self.alliance = alliance['name']
        self.ship_id = ship['id']
        self.ship = ship['name']
        solarSystem = json['solarSystem']
        self.system_id = solarSystem['id']
        self.system = solarSystem['name']
        # CREST Killmails are always verified
        self.verified = True
        # Parse the timestamp
        time_struct = time.strptime(json['killTime'], '%Y.%m.%d %H:%M:%S')
        self.timestamp = dt.datetime(*(time_struct[0:6]),
                tzinfo=dt.timezone.utc)
