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


class Killmail(object):
    def __init__(self, **kwargs):
        for attr in ('kill_id', 'ship_id', 'ship', 'pilot_id', 'pilot',
                'corp_id', 'corp', 'alliance_id', 'alliance', 'verified',
                'url', 'value', 'timestamp'):
            try:
                setattr(self, attr, kwargs[attr])
            except KeyError:
                try:
                    setattr(self, attr, None)
                except AttributeError:
                    pass
        super(Killmail, self).__init__(**kwargs)

    def __str__(self):
        return "{kill_id}: {pilot} lost a {ship}. Verified: {verified}.".\
                format(kill_id=self.kill_id, pilot=self.pilot, ship=self.ship,
                        verified=self.verified)

    def __iter__(self):
        yield ('id', self.kill_id)
        yield ('ship_type', self.ship)
        yield ('corporation', self.corp)
        yield ('alliance', self.alliance)
        yield ('killmail_url', self.url)
        yield ('base_payout', self.value)
        yield ('kill_timestamp', self.timestamp)


class RequestsSessionMixin(object):
    def __init__(self, requests_session=None, **kwargs):
        if requests_session is None:
            self.requests_session = requests.Session()
        else:
            self.requests_session = request_session
        super(RequestsSessionMixin, self).__init__(**kwargs)


def SQLShipMixin(*args, **kwargs):
    """Class factory for mixin classes to retrieve ship names from a database.

    Uses SQLAlchemy internally for SQL operations so as to make it usable on as
    many platforms as possible. The arguments passed to this function are
    passed directly to :py:func:`sqlalchemy.create_engine`, so feel free to use
    whatver arguemtns you wish. As long as the database has an ``invTypes``
    table with ``typeID`` and ``typeName`` columns and there's a DBAPI driver
    supported by SQLAlchemy, this mixin should work.
    """
    class _SQLMixin(object):
        engine = create_engine(*args, **kwargs)
        metadata = MetaData(bind=engine)
        invTypes = Table('invTypes', metadata, autoload=True)

        def __init__(self, *args, **kwargs):
            super(_SQLMixin, self).__init__(*args, **kwargs)

        @property
        def ship(self):
            conn = self.engine.connect()
            # Construct the select statement
            sel = select([self.invTypes.c.typeName])
            sel = sel.where(self.invTypes.c.typeID == self.ship_id)
            sel = sel.limit(1)
            # Get the results
            result = conn.execute(sel)
            row = result.fetchone()
            # Cleanup
            result.close()
            conn.close()
            return row[0]

    return _SQLMixin


class EveMDShipNameMixin(RequestsSessionMixin):
    # Yeah, using regexes on XML. Deal with it.
    evemd_regex = re.compile(
            r'<val id="\d+">(?P<ship_name>[A-Za-z0-9]+)</val>')

    def __init__(self, user_agent=None, **kwargs):
        if user_agent is not None or user_agent != '':
            self.user_agent=user_agent
        else:
            self.user_agent = 'Unconfigured EVE-SRP Mixin'
        super(EveMDShipNameMixin, self).__init__(**kwargs)

    @property
    def ship(self):
        resp = self.requests_session.get(
                'http://api.eve-marketdata.com/api/type_name.xml', params=
                {
                    'char_name': quote(self.user_agent),
                    'v': self.ship_id
                })
        if resp.status_code == requests.codes.ok:
            match = self.evemd_regex.search(resp.text)
            if match:
                return match.group('ship_name')
        return None


class ZKillmail(Killmail, RequestsSessionMixin):
    zkb_regex = re.compile(r'/detail/(?P<kill_id>\d+)/?')

    def __init__(self, url, **kwargs):
        super(ZKillmail, self).__init__(**kwargs)
        self.url = url
        match = self.zkb_regex.search(url)
        if match:
            self.kill_id = int(match.group('kill_id'))
        else:
            raise ValueError("Killmail ID was not found in URL '{}'".
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
        self.pilot_id = victim['characterID']
        self.pilot = victim['characterName']
        self.corp_id = victim['corporationID']
        self.corp = victim['corporationName']
        self.alliance_id = victim['allianceID']
        self.alliance = victim['allianceName']
        self.ship_id = victim['shipTypeID']
        # For consistency, store self.value in millions. Decimal is being used
        # for precision at large values.
        value = Decimal(json['zkb']['totalValue'])
        self.value = value / 1000000
        # Parse the timestamp
        time_struct = time.strptime(json['killTime'], '%Y-%m-%d %H:%M:%S')
        self.timestamp = dt.datetime(*(time_struct[0:6]),
                tzinfo=dt.timezone.utc)

    @property
    def verified(self):
        return self.kill_id > 0

    def __str__(self):
        parent = super(ZKillmail, self).__str__()
        return "{parent} From ZKillboard at {url}".format(parent=parent,
                url=self.url)


class CRESTMail(Killmail, RequestsSessionMixin):
    crest_regex = re.compile(r'/killmails/(?P<kill_id>\d+)/[0-9a-f]+/')

    def __init__(self, url, **kwargs):
        super(CRESTMail, self).__init__(**kwargs)
        self.url = url
        match = self.crest_regex.search(self.url)
        if match:
            self.kill_id = match.group('kill_id')
        else:
            raise ValueError("Killmail ID was not found in URL '{}'".
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
        # CREST Killmails are always verified
        self.verified = True
        # Parse the timestamp
        time_struct = time.strptime(json['killTime'], '%Y.%m.%d %H:%M:%S')
        self.timestamp = dt.datetime(*(time_struct[0:6]),
                tzinfo=dt.timezone.utc)
