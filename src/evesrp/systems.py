import re
from flask import current_app
from .util.crest import check_crest_response, NameLookup
from . import static_data


REGION_TYPE = 'application/vnd.ccp.eve.Region-v1+json'
CONSTELLATION_TYPE = 'application/vnd.ccp.eve.Constellation-v1+json'
SYSTEM_TYPE = 'application/vnd.ccp.eve.System-v1+json'


region_names = NameLookup(static_data.region_names, 'regions', REGION_TYPE)


constellation_names = NameLookup(
        static_data.constellation_names,
        'constellations',
        CONSTELLATION_TYPE)


system_names = NameLookup(static_data.system_names, 'systems', SYSTEM_TYPE)


class ConstellationRegionLookup(NameLookup):

    def __init__(self):
        super(ConstellationRegionLookup, self).__init__(
                static_data.constellations_to_regions,
                'constellations',
                CONSTELLATION_TYPE,
                'region.href')

    def __getitem__(self, key):
        parent_item = super(ConstellationRegionLookup, self).__getitem__(key)
        # parent item will either be a CREST URL or an integer type ID
        if isinstance(parent_item, int):
            return parent_item
        resp = current_app.requests_session.get(parent_item,
                headers={'Accept': REGION_TYPE})
        if check_crest_response(resp) and resp.status_code == 200:
            self._dict[key] = resp.json()['id']
        else:
            message = "Cannot find the name for the ID requested: {}"\
                    .format(key)
            raise KeyError(message)
        return self._dict[key]


systems_constellations = NameLookup(static_data.systems_to_constellations,
                                    'systems',
                                    SYSTEM_TYPE,
                                    'constellation.id')

constellations_regions = ConstellationRegionLookup()
