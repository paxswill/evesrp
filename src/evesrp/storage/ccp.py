import six
import evesrp.esi.client
from evesrp import static_data


class CcpStore(object):

    def __init__(self, requests_session=None):
        self.client = evesrp.esi.client.create_client(requests_session)

    def _single_search(self, category, query):
        request = self.client.Search.get_search(search=query,
                                                strict=True,
                                                categories=[category])
        results = request.result()[category]
        if results is None:
            # No result
            return None
        elif len(results) == 1:
            # If there's only one result, hooray, easy
            return request.result()[category][0]
        else:
            # Multiple results, like if there's a name with a '.' at the end.
            # This means we get to go through and find the right ID
            name_lookup = getattr(self, 'get_{}_name'.format(category))
            for result_id in results:
                name = name_lookup(result_id)
                if name == query:
                    return result_id


    def get_region_id(self, name):
        return self._single_search('region', name)

    def get_region_name(self, ccp_id):
        request = self.client.Universe.get_universe_regions_region_id(
                region_id=ccp_id)
        return request.result()['name']

    def get_constellation_id(self, name):
        return self._single_search('constellation', name)

    def get_constellation_name(self, ccp_id):
        request = self.client.Universe.\
            get_universe_constellations_constellation_id(
                constellation_id=ccp_id)
        return request.result()['name']

    def get_system_id(self, name):
        return self._single_search('solarsystem', name)

    def get_system_name(self, ccp_id):
        request = self.client.Universe.get_universe_systems_system_id(
            system_id=ccp_id)
        return request.result()['name']

    def get_character_id(self, name):
        # Same with corporations, ESI only considers the current holder of a
        # name, not past names (ex: a name was freed up when CCP cleared
        # out names someimte around 2013 or 2014. I now have the name, and only
        # my character is returned).
        return self._single_search('character', name)

    def get_character_name(self, ccp_id):
        request = self.client.Character.get_characters_character_id(
            character_id=ccp_id)
        return request.result()['name']

    def get_corporation_id(self, name):
        # Note, ESI only returns active corporations (at least as of
        # 2017-02-15), so we don't have to deal with duplicates.
        return self._single_search('corporation', name)

    def get_corporation_name(self, ccp_id):
        request = self.client.Corporation.get_corporations_corporation_id(
            corporation_id=ccp_id)
        return request.result()['corporation_name']

    def get_alliance_id(self, name):
        return self._single_search('alliance', name)

    def get_alliance_name(self, ccp_id):
        request = self.client.Alliance.get_alliances_names(
            alliance_ids=[ccp_id])
        return request.result()[0]['alliance_name']

    def get_type_id(self, name):
        # it is possible for there to be multiple types for a single name. A
        # good example is the query 'Cruor' will return two results.
        request = self.client.Search.get_search(search=name,
                                                strict=True,
                                                categories=['inventorytype'])
        for result in request.result()['inventorytype']:
            type_info = self.client.Universe.get_universe_types_type_id(
                type_id=result).result()
            if type_info['published']:
                return result
        # If none are published, return the first one
        return request.result()[0]

    def get_type_name(self, ccp_id):
        request = self.client.Universe.get_universe_types_type_id(
            type_id=ccp_id)
        return request.result()['name']


class CachingCcpStore(CcpStore):

    def _try_flipped_static_map(self, static_map, name, getter_name):
        flipped = {v: k for k, v in six.iteritems(static_map)}
        try:
            return flipped[name]
        except KeyError:
            ccp_id = getattr(super(CachingCcpStore, self), getter_name)(name)
            static_map[ccp_id] = name
            return ccp_id

    def _try_static_map(self, static_map, ccp_id, getter_name):
        if ccp_id not in static_map:
            name = getattr(super(CachingCcpStore, self), getter_name)(ccp_id)
            static_map[ccp_id] = name
        return static_map[ccp_id]

    def get_region_id(self, name):
        return self._try_flipped_static_map(static_data.region_names, name,
                                            'get_region_id')

    def get_region_name(self, ccp_id):
        return self._try_static_map(static_data.region_names, ccp_id,
                                    'get_region_name')

    def get_constellation_id(self, name):
        return self._try_flipped_static_map(static_data.region_names, name,
                                            'get_constellation_id')

    def get_constellation_name(self, ccp_id):
        return self._try_static_map(static_data.region_names, ccp_id,
                                    'get_region_name')

    def get_system_id(self, name):
        return self._try_flipped_static_map(static_data.region_names, name,
                                            'get_system_id')

    def get_system_name(self, ccp_id):
        return self._try_static_map(static_data.region_names, ccp_id,
                                    'get_region_name')

    def get_type_id(self, name):
        return self._try_flipped_static_map(static_data.ships, name,
                                            'get_type_id')

    def get_type_name(self, ccp_id):
        return self._try_static_map(static_data.ships, ccp_id, 'get_type_name')
