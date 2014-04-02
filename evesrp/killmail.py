from functools import partial
import re
import sys
from urllib.parse import urlparse, urlunparse, quote

import requests


class Killmail(object):
    def __init__(self, **kwargs):
        for attr in ('kill_id', 'ship_id', 'ship', 'pilot_id', 'pilot',
                'corp_id', 'corp', 'alliance_id', 'alliance', 'verified'):
            try:
                setattr(self, attr, kwargs[attr])
            except AttributeError:
                pass
            except KeyError:
                setattr(self, attr, None)
        super(Killmail, self).__init__(**kwargs)

    def __str__(self):
        return "{kill_id}: {pilot} lost a {ship}. Verified: {verified}.".\
                format(kill_id=self.kill_id, pilot=self.pilot, ship=self.ship,
                        verified=self.verified)


class RequestsSessionMixin(object):
    def __init__(self, requests_session=None, **kwargs):
        if requests_session is None:
            self.requests_session = requests.Session()
        else:
            self.requests_session = request_session
        super(RequestsSessionMixin, self).__init__(**kwargs)


class SQLShipNameMixin(object):

    select_stmt = {
        'qmark':
            'SELECT typeName FROM invTypes WHERE invTypes.typeID=?;',
        'numeric':
            'SELECT typeName FROM invTypes WHERE invTypes.typeID=:1;',
        'named':
            'SELECT typeName FROM invTypes WHERE invTypes.typeID=:type',
        'format':
            'SELECT typeName FROM invTypes WHERE invTypes.typeID=%s;',
        'pyformat':
            'SELECT typeName FROM invTypes WHERE invTypes.typeID=%(type);'
    }


    def __init__(self, driver=None, connect_args=None, **kwargs):
        if driver is not None:
            self.__class__.driver = driver
        if connect_args is not None:
            self.__class.connect_args = connect_args
        super(SQLShipNameMixin, self).__init__(**kwargs)

    @property
    def ship(self):
        con = self.driver.connect(self.connect_args)
        cursor = con.cursor()
        module = sys.modules[cursor.__class__.__module__]
        # Attempt to support as many DB backend as possible
        if module.paramstyle in ('qmark', 'format', 'numeric'):
            results = cursor.execute(
                    self.select_stmt[module.paramstyle], (self.ship_id,))
        elif module.paramstyle in ('named', 'pyformat'):
            results = cursor.execute(self.select_stmt[module.paramstyle],
                    {'type': self.ship_id})
        result = results.fetchone()[0]
        con.close()
        return result


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
        self.verified = True
