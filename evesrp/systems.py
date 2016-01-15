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


class ConstellationRegionLookup(NameLookup):

    def __init__(self):
        super(ConstellationRegionLookup, self).__init__(
                static_data.constellations_to_regions,
                CONSTELLATION_SLUG,
                CONSTELLATION_TYPE,
                'region.href')

    def __getitem__(self, key):
        parent_item = super(ConstellationRegionLookup, self).__getitem__(key)
        # parent item will either be a CREST URL or an integer type ID
        if isinstance(parent_item, int):
            return parent_item
        match = re.match(REGION_SLUG.replace('{}', '(.*)'), parent_item)
        if not match:
            message = "Cannot find the name for the ID requested: {}"\
                    .format(key)
            raise KeyError(message)
        self._dict[key] = int(match.group(1))
        return self._dict[key]


systems_constellations = NameLookup(static_data.systems_to_constellations,
                                    SYSTEM_SLUG,
                                    SYSTEM_TYPE,
                                    'constellation.id')

constellations_regions = ConstellationRegionLookup()
