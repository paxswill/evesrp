import re
from flask import current_app
from .util.crest import check_crest_response, NameLookup
from . import static_data


REGION_TYPE = 'application/vnd.ccp.eve.Region-v1+json'
CONSTELLATION_TYPE = 'application/vnd.ccp.eve.Constellation-v1+json'
SYSTEM_TYPE = 'application/vnd.ccp.eve.System-v1+json'

REGION_SLUG = 'https://public-crest.eveonline.com/regions/{}/'
CONSTELLATION_SLUG = 'https://public-crest.eveonline.com/constellations/{}/'
SYSTEM_SLUG = 'https://public-crest.eveonline.com/solarsystems/{}/'


region_names = NameLookup(static_data.region_names, REGION_SLUG, REGION_TYPE)


constellation_names = NameLookup(
        static_data.constellation_names,
        CONSTELLATION_SLUG,
        CONSTELLATION_TYPE)


system_names = NameLookup(static_data.system_names, SYSTEM_SLUG, SYSTEM_TYPE)


class SystemConstellationLookup(object):

    def __init__(self):
        self._dict = {}

    def __getitem__(self, key):
        if not isinstance(key, int):
            raise TypeError("Invalid ID for name lookup: '{}'".\
                    format(key))
        if key not in self._dict:
            sys_resp = current_app.requests_session.get(
                    SYSTEM_SLUG.format(key),
                    headers={'Accept': SYSTEM_TYPE})
            if not check_crest_response(sys_resp) or \
                    sys_resp.status_code != 200:
                message = "Cannot find the name for the ID requested [{}]: {}"\
                        .format(sys_resp.status_code, key)
                raise KeyError(message)
            match = re.match(CONSTELLATION_SLUG.replace('{}', '(.*)'),
                    sys_resp.json()['constellation']['href'])
            if not match:
                message = "Cannot find the name for the ID requested: {}"\
                        .format(key)
                raise KeyError(message)
            self._dict[key] = int(match.group(1))
        return self._dict[key]


class ConstellationRegionLookup(object):

    def __init__(self):
        self._dict = {}

    def __getitem__(self, key):
        if not isinstance(key, int):
            raise TypeError("Invalid ID for name lookup: '{}'".\
                    format(key))
        if key not in self._dict:
            const_resp = current_app.requests_session.get(
                    CONSTELLATION_SLUG.format(key),
                    headers={'Accept': CONSTELLATION_TYPE})
            if not check_crest_response(const_resp) or \
                    const_resp.status_code != 200:
                message = "Cannot find the name for the ID requested [{}]: {}"\
                        .format(const_resp.status_code, key)
                raise KeyError(message)
            match = re.match(REGION_SLUG.replace('{}', '(.*)'),
                    const_resp.json()['region']['href'])
            if not match:
                message = "Cannot find the name for the ID requested: {}"\
                        .format(key)
                raise KeyError(message)
            self._dict[key] = int(match.group(1))
        return self._dict[key]


systems_constellations = SystemConstellationLookup()
constellations_regions = ConstellationRegionLookup()
