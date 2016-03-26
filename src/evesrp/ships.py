from __future__ import unicode_literals

from .util.crest import NameLookup
from . import static_data




ships = NameLookup(static_data.ships,
        'https://public-crest.eveonline.com/types/{}/',
        'application/vnd.ccp.eve.ItemType-v3+json')
