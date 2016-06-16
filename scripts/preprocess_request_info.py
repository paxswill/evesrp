#!/usr/bin/env python
from __future__ import print_function

from collections import namedtuple
import datetime as dt
import time
import json
import sys
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError


class RateLimitedCache(HTTPAdapter):

    def __init__(self, requests_per_second=None, *args, **kwargs):
        super(RateLimitedCache, self).__init__(*args, **kwargs)
        self.interval = 1.0 / requests_per_second
        self.last_request = 0.0
        self.cache = {}

    def send(self, request,
             stream=False,
             timeout=None,
             verify=True,
             cert=None,
             proxies=None):
        try:
            return self.cache[request.url]
        except KeyError:
            current_time = time.clock()
            elapsed_time = current_time - self.last_request
            if elapsed_time < self.interval:
                time.sleep(self.interval)
                return self.send(request, stream, timeout, verify, cert,
                        proxies)
            else:
                self.last_request = current_time
                def super_send():
                    return super(RateLimitedCache, self).send(request,
                            stream, timeout, verify, cert, proxies)
                for attempt_num in range(5):
                    try:
                        response = super_send()
                    except requests.exceptions.ConnectionError as e:
                        time.sleep(2)
                    else:
                        break
                else:
                    raise
                self.cache[request.url] = response
                return self.cache[request.url]


session = requests.Session()
# Eve XML API rate limit is 30/sec. Decrease by one for some wiggle room
session.mount('https://api.eveonline.com',
              RateLimitedCache(requests_per_second=29))
session.headers.update(
        {'User-Agent': 'EVE-SRPDBMigrator/1.0 (paxswill@paxswill.com'})


class Period(object):

    def __init__(self, start, end=None, length=None):
        # Either start and length, start and end, or just start must be at
        # least be given. If only start is given, the period is assumed to
        # continue to now.
        self.start = start
        if end is not None:
            self.end = end
        elif length is not None:
            self.end = self.start + length
        else:
            self.end = dt.datetime.max


    def __contains__(self, value):
        if not isinstance(value, dt.datetime):
            raise TypeError("Period.__contains__ must be called with a "
                            "datetime")
        return value >= self.start and value < self.end

    def __hash__(self):
        return hash(str(self.start) + str(self.end))

    def __eq__(self, other):
        return self.start == other.start and self.end == other.end

    def __str__(self):
        return '{}_{}'.format(self.start.isoformat(), self.end.isoformat())


class Corporation(object):

    def __init__(self, ccp_id=None, name=None, known_data=None):
        if ccp_id == name and ccp_id is None:
            raise ValueError("At least one of name or CCP ID must be given")
        # Set the CCP ID
        if ccp_id is not None:
            self.ccp_id = ccp_id
        else:
            ccp_resp = session.get(('https://api.eveonline.com/eve/'
                                    'CharacterID.xml.aspx'),
                                   params={'names': name})
            assert ccp_resp.status_code == 200
            soup = BeautifulSoup(ccp_resp.text, 'xml')
            self.ccp_id = int(soup.find('row').attrs['characterID'])
        # Set up
        if known_data is not None and ccp_id in known_data:
            self.data = known_data[ccp_id]
        else:
            self.data = {}
        if name is not None and 'name' not in self.data:
            self.data['name'] = name

    @property
    def name(self):
        if 'name' not in self.data:
            name_element = self.ccp_xml.find('.//corporationName')
            self.data['name'] = name_element.text
        return self.data['name']

    def alliance_id(self, timestamp=None):
        # Fail fast for NPC corps. NPC corp IDs are 1000001 (Doomheim) through
        # 1000274 (Some DUST corp I think). Leaving a bit of wiggle room for
        # future updates.
        if self.ccp_id >= 1000001 and self.ccp_id < 1000300:
            return None
        if timestamp is None:
            timestamp = dt.datetime.now()
        if 'alliances' not in self.data:
            alliances = {}
            history_table = self.dotlan.find(name='h2',
                                             string='Alliance History')\
                .find_next_sibling('table')
            # If a corp has never been in an alliance, it doesn't have a
            # history.
            if history_table is None:
                return None
            rows = history_table.find_all('tr')
            # The first row is a header
            last_end = dt.datetime.now()
            for row in rows[1:]:
                columns = row.find_all('td')
                start_date = dt.datetime.strptime(columns[3].string,
                                                  '%Y-%m-%d %H:%M:%S')
                if columns[4].string == '-':
                    period = Period(start_date)
                else:
                    end_date = dt.datetime.strptime(columns[4].string,
                                                    '%Y-%m-%d %H:%M:%S')
                    period = Period(start_date, end_date)
                # The coupling is strong here
                alliance_id = columns[1].find('a').attrs['class'][1][11:]
                alliance_id = int(alliance_id)
                alliances[period] = alliance_id
            self.data['alliances'] = alliances
        for period, alliance_id in self.data['alliances'].items():
            if timestamp in period:
                return alliance_id
        return None

    def alliance(self, timestamp=None):
        if timestamp is None:
            timestamp = dt.datetime.now()
        return Alliance(ccp_id=self.alliance_id(timestamp))

    @property
    def dotlan(self):
        if not hasattr(self, '_dotlan'):
            dotlan_url = 'http://evemaps.dotlan.net/corp/{}/alliances'.format(
                self.ccp_id)
            dotlan_resp = session.get(dotlan_url)
            assert dotlan_resp.status_code == 200
            self._dotlan = BeautifulSoup(dotlan_resp.text)
        return self._dotlan

    @property
    def ccp_xml(self):
        if not hasattr(self, '_ccp_xml'):
            ccp_resp = session.get(('https://api.eveonline.com/corp/'
                                    'CorporationSheet.xml.aspx'),
                                   params={'corporationID': ccp_id})
            assert ccp_resp.status_code == 200
            self._ccp_xml = BeautifulSoup(ccp_resp, 'xml')
        return self._ccp_xml


class Alliance(object):

    def __init__(self, ccp_id=None, name=None, known_data=None):
        if ccp_id == name and ccp_id is None:
            raise ValueError("At least one of name or CCP ID must be given")
        if ccp_id is not None:
            self.ccp_id = ccp_id
        else:
            ccp_resp = session.get(('https://api.eveonline.com/eve/'
                                    'CharacterID.xml.aspx'),
                                   params={'names': name})
            assert ccp_resp.status_code == 200
            soup = BeautifulSoup(ccp_resp.text, 'xml')
            self.ccp_id = int(soup.find('row').attrs['characterID'])
        if known_data is not None and ccp_id in known_data:
            self.data = known_data[ccp_id]
        else:
            self.data = {}
        if name is not None and 'name' not in self.data:
            self.data['name'] = name

    @property
    def name(self):
        if 'name' not in self.data:
            alliance_url = self.crest_root['alliances']['href']
            alliance_url += str(self.ccp_id) + '/'
            resp = session.get(alliance_url)
            assert resp.status_code == 200
            self.data['name'] = resp.json()['name']
        return self.data['name']

    @property
    def crest_root(self):
        if not hasattr(self, '_crest_root'):
            root_resp = session.get('https://crest-tq.eveonline.com')
            assert root_resp.status_code == 200
            self._crest_root = root_resp.json()
        return self._crest_root


class MigrationEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, Period):
            return {
                '_type': 'period',
                'start': o.start.isoformat(),
                'end': o.end.isoformat(),
            }
        elif isinstance(o, Corporation):
            # For those corps never in an alliance (ex: NPC corps)
            corp = {
                '_type': 'corporation',
                'name': o.name,
                'id': o.ccp_id,
            }
            if 'alliances' in o.data:
                corp['alliances'] = {str(p): a for p, a in
                                     o.data['alliances'].items()}
            return corp
        elif isinstance(o, Alliance):
            return {
                '_type': 'alliance',
                'name': o.name,
                'id': o.ccp_id,
            }
        raise TypeError


def parse_isoformat(iso_string):
    # Try with and without milliseconds
    try:
        return dt.datetime.strptime(iso_string, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        return dt.datetime.strptime(iso_string, '%Y-%m-%dT%H:%M:%S.%f')



def json_object_hook(json_obj):
    if json_obj.get('_type') == 'period':
        start_date = parse_isoformat(json_obj['start'])
        end_date = parse_isoformat(json_obj['end'])
        return Period(start=start_date, end=end_date)
    elif json_obj.get('_type') == 'corporation':
        corp = Corporation(ccp_id=json_obj['id'], name=json_obj['name'])
        # Removing empty alliance dicts just in case they sneak in
        if 'alliances' in json_obj and len(json_obj['alliances']) != 0:
            alliances = {}
            for period_string, alliance in json_obj['alliances'].items():
                start_string, end_string = period_string.split('_')
                period = Period(start=parse_isoformat(start_string),
                                end=parse_isoformat(end_string))
                alliances[period] = alliance
            corp.data['alliances'] = alliances
        return corp
    elif json_obj.get('_type') == 'alliance':
        return Alliance(ccp_id=json_obj['id'], name=json_obj['name'])
    else:
        return json_obj


class FuzzworksTypeLookup(object):

    def __init__(self, starting_data):
        self.data = starting_data

    def __getitem__(self, key):
        if key not in self.data:
            fuzzworks_resp = session.get('https://www.fuzzwork.co.uk/api/'
                                         'typeid.php?typename={}'.format(
                                             key))
            fuzzworks_json = fuzzworks_resp.json()
            if fuzzworks_json['typeName'] == 'bad item':
                raise KeyError("Type ID not found for name '{}'".format(
                    key))
            else:
                self.data[key] = fuzzworks_json['typeID']
        return self.data[key]


class SRPApp(object):

    def __init__(self, base_url, api_key, data_path='srp_requests.json'):
        self.base_url = base_url
        self.api_key = api_key
        self.data_path = data_path
        try:
            with open(self.data_path, 'r') as data_file:
                data = json.load(data_file, object_hook=json_object_hook)
            requests_data = data.get('requests', {})
            self.requests_data = {int(k): v for k, v in requests_data.items()}
            entity_data = data.get('entities', {})
            self.entity_data = {int(k): v for k, v in entity_data.items()}
        except IOError:
            self.requests_data = {}
            self.entity_data = {}

    @property
    def requests(self):
        # Iterate through the data for each individual request an API key has
        # access to.
        page_slug = self.base_url + '/request/all/page/{}'
        page_num = 1
        resp = session.get(page_slug.format(page_num),
                           headers={'Accept': 'application/json'},
                           params={'apikey': self.api_key})
        assert resp.status_code == 200
        while True:
            srp_requests = resp.json()['requests']
            if len(srp_requests) == 0:
                break
            for request in srp_requests:
                yield request
            # API requests have a limit of 200 per page
            if len(srp_requests) < 200:
                break
            page_num += 1
            # Try 3 times
            for attempt_num in range(3):
                try:
                    resp = session.get(page_slug.format(page_num),
                                   headers={'Accept': 'application/json'},
                                   params={'apikey': self.api_key})
                except requests.exceptions.ConnectionError as e:
                    if attempt_num == 2:
                        raise
                else:
                    break

    @property
    def types(self):
        if not hasattr(self, '_types'):
            types = {}
            category_resp = session.get(
                self.crest_root['itemCategories']['href'])
            for category in category_resp.json()['items']:
                if category['name'] == 'Ship':
                    ship_resp = session.get(category['href'])
                    break
            for group in ship_resp.json()['groups']:
                group_resp = session.get(group['href'])
                types.update(
                    {t['name']: t['id'] for t in group_resp.json()['types']}
                )
            # Fixing prerelease CCP data included in a release of EVE-SRP
            types['Minmatar Force Auxiliary'] = types['Lif']
            types['Caldari Force Auxiliary'] = types['Minokawa']
            types['Amarr Force Auxiliary'] = types['Apostle']
            types['Gallente Force Auxiliary'] = types['Ninazu']
            # Set up a custom object to look up missing values with Steve
            # Ronuken's typeName -> typeID API
            self._types = FuzzworksTypeLookup(types)
        return self._types

    @property
    def locations(self):
        if not hasattr(self, '_locations'):
            locations = {}
            for location_key in ('systems', 'constellations', 'regions'):
                resp = session.get(self.crest_root[location_key]['href'])
                locations.update(
                    {item['name']: item['id'] for item in resp.json()['items']}
                )
            self._locations = locations
        return self._locations

    @property
    def crest_root(self):
        if not hasattr(self, '_crest_root'):
            root_resp = session.get('https://crest-tq.eveonline.com/')
            self._crest_root = root_resp.json()
        return self._crest_root

    def _migrate_request(self, request):

        def zkillboard_api():
            killmail_url = 'https://zkillboard.com/api/killID/{}'.format(
                request['id'])
            killmail_resp = session.get(killmail_url)
            assert killmail_resp.status_code == 200
            killmail = killmail_resp.json()[0]
            return killmail

        # For some reason, sometimes corp name is empty.
        if request['corporation'] == '':
            victim = zkillboard_api()['victim']
            corp_name = victim['corporationName']
        else:
            corp_name = request['corporation']
        # Get Corp and Alliance IDs
        corp = Corporation(name=corp_name, known_data=self.entity_data)
        # CCP's API returns 0 for closed corps, so try to get the info from zKB
        if corp.ccp_id == 0:
            victim = zkillboard_api()['victim']
            corp = Corporation(ccp_id=victim['corporationID'],
                               name=victim['corporationName'])
        try:
            kill_timestamp = dt.datetime.strptime(
                request['kill_timestamp'],
                '%a, %d %b %Y %H:%M:%S GMT')
        except ValueError:
            kill_timestamp = dt.datetime.strptime(
                request['kill_timestamp'],
                '%Y-%m-%dT%H:%M:%S')
        alliance_id = corp.alliance_id(kill_timestamp)
        entities = [corp]
        if alliance_id is not None:
            alliance = Alliance(ccp_id=alliance_id,
                                known_data=self.entity_data)
            entities.append(alliance)
        # Save the data we've just looked up
        for entity in entities:
            if entity.ccp_id not in self.entity_data:
                self.entity_data[entity.ccp_id] = entity
        # Skip recording the final request data if the type ID is missing
        return {
            'corporation_id': corp.ccp_id,
            'alliance_id': alliance_id,
            'system_id': self.locations[request['system']],
            'constellation_id': self.locations[request['constellation']],
            'region_id': self.locations[request['region']],
            'type_id': self.types[request['ship']],
        }

    def save(self, save_path=None):
        if save_path is None:
            save_path = self.data_path
        with open(save_path, 'w') as data_file:
            # JSON requires objects (dicts) to have string keys
            entities = {str(k): v for k, v in self.entity_data.items()}
            srp_requests = {str(k): v for k, v in self.requests_data.items()}
            json.dump(dict(entities=entities,
                           requests=srp_requests),
                      data_file,
                      cls=MigrationEncoder)

    def migrate_requests(self,
                         catch_exceptions=False,
                         save_on_exceptions=True):
        no_errors = True
        for request_num, request in enumerate(self.requests):
            if request_num % 100 == 0:
                print("Processed {} requests".format(request_num))
                self.save()
            if request['id'] not in self.requests_data:
                try:
                    request_data = self._migrate_request(request)
                # Yes, catching all Exceptions on purpose.
                except (ValueError, LookupError, AttributeError,
                        AssertionError, TypeError) as e:
                    no_errors = False
                    if save_on_exceptions:
                        self.save()
                    print("On Request #{}: {}".format(request['id'], str(e)))
                    if not catch_exceptions:
                        raise
                except KeyboardInterrupt:
                    self.save()
                    no_errors = False
                    break
                else:
                    self.requests_data[request['id']] = request_data
        return no_errors


def main():
    if len(sys.argv) < 3:
        print("Usage: {} <base_url> <api_key> [data_path]".format(sys.argv[0]))
        sys.exit(1)
    app = SRPApp(*sys.argv[1:])
    app.migrate_requests(catch_exceptions=True)
    sys.exit(0)


if __name__ == '__main__':
    main()
