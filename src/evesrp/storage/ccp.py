try:
    from collections.abc import Sequence
except ImportError:
    from collections import Sequence
import warnings

import requests
import six

from evesrp import static_data
from . import errors


class CcpStore(object):

    def __init__(self, requests_session=None):
        if requests_session is None:
            requests_session = requests.Session()
        self.session = requests_session

    def _esi_request(self, version, path, method='GET', post_data=None,
                     json_data=None, **params):
        params.setdefault('datasource', 'tranquility')
        # All ESI paths end with '/' (except for the one to the Swagger
        # definition).
        if path[-1] != '/':
            path += '/'
        if path[0] == '/':
            path = path[1:]
        url = "https://esi.tech.ccp.is/{version}/{path}".format(
            version=version, path=path)
        # Only query params are used in routes (for those routes I'm using so
        # far).
        query_params = {}
        path_params = {}
        for key, value in six.iteritems(params):
            if isinstance(value, bool):
                value = 'true' if value else 'false'
            elif isinstance(value, Sequence) and \
                    not isinstance(value, six.string_types):
                value = ','.join(value)
            if '{{{param}}}'.format(param=key) in path:
                path_params[key] = value
            else:
                query_params[key] = value
        parameter_url = url.format(**path_params)
        kwargs = {
            'params': query_params,
        }
        if method == 'POST':
            if json_data is not None:
                kwargs['json'] = json_data
            elif post_data is not None:
                kwargs['data'] = post_data
        resp = self.session.request(method, parameter_url, **kwargs)
        try:
            resp.json()
        except ValueError as exc:
            new_exc = errors.EsiError(response)
            six.raise_from(new_exc, exc)
        # Check for deprecation headers
        if 'warning' in resp.headers:
            warnings.warn(resp.headers['warning'], errors.EsiWarning)
        return resp

    def _single_search(self, category, query):
        search_response = self._esi_request('v1', 'search', strict=True,
                                            categories=[category],
                                            search=query)
        search_json = search_response.json()
        if category not in search_json:
            if category == 'inventorytype':
                kind = 'type'
            elif category == 'solar_system':
                kind = 'system'
            else:
                kind = category
            raise errors.NotFoundError(kind=kind, identifier=query)
        elif len(search_json[category]) == 1:
            return {
                u'name': query,
                u'id': search_json[category][0],
            }
        else:
            # Multiple results
            # This can happen if the query string is a substring of the other
            # results. Because we're only searching for full names, this can
            # happen if there's a dot at the end or things like that. Because
            # we're also searching for exact matches, we then just look up all
            # the names for the IDs and figure it out from there
            result_ids = search_json[category]
            names_response = self._esi_request('v2', 'universe/names/',
                                               method='POST',
                                               json_data=result_ids)
            names_json = names_response.json()
            # the category names used in /universe/names/ are different than
            # /search/
            if category == 'inventorytype':
                names_category = 'inventory_type'
            elif category == 'solar_system':
                names_category = 'solar_system'
            else:
                names_category = category
            # Find the matching name
            for name_result in names_json:
                if name_result[u'category'] == names_category and \
                        name_result[u'name'] == query:
                    return {
                        u'id': name_result[u'id'],
                        u'name': query,
                    }
            else:
                exc = errors.EsiError(names_response)
                exc.error = ("ESI /search/ returned IDs that /universe/names/ "
                             "can't resolve ({}).").format(
                                 ", ".join(result_ids))
                raise exc
        return search_results

    def _base_constellation(self, constellation_id):
        esi_path = '/universe/constellations/{constellation_id}/'
        esi_response = self._esi_request('v1', esi_path,
                                         constellation_id=constellation_id)
        # NOTE As of 2017-03-07, ESI returns 500 instead of 404 for
        # constellations not found. Github issue ccpgames/esi-issues#307
        # When this is fixed, change back to checking for 404, stop
        # clearing the server error message from the results, and stop setting
        # the status code to 404 for all 500 errors.
        if esi_response.status_code in (500, 404):
            raise errors.NotFoundError(kind='constellation',
                                       identifier=constellation_id)
        return esi_response

    def _base_system(self, system_id):
        esi_response = self._esi_request('v2',
                                         '/universe/systems/{system_id}/',
                                         system_id=system_id)
        # NOTE As of 2017-03-07, ESI returns 500 instead of 404 for systems
        # not found. Github issue ccpgames/esi-issues#307
        # When this is fixed, change back to checking for 404 and stop
        # clearing the server error message from the results and setting the
        # code to 404 on all 500s.
        if esi_response.status_code in (500, 404):
            raise errors.NotFoundError(kind='system',
                                       identifier=system_id)
        return esi_response

    def get_region(self, region_name=None, region_id=None,
                   constellation_name=None, constellation_id=None,
                   system_name=None, system_id=None):
        if region_id is not None:
            esi_response = self._esi_request('v1',
                                             '/universe/regions/{region_id}/',
                                             region_id=region_id)
            esi_json = esi_response.json()
            if esi_response.status_code == 200:
                return {
                    u'name': esi_json[u'name'],
                    u'id': region_id,
                }
            # NOTE As of 2017-03-07, ESI returns 500 instead of 404 for regions
            # not found. Github issue ccpgames/esi-issues#307
            # When this is fixed, change back to checking for 404 and stop
            # clearing the server error message from the results
            elif esi_response.status_code == 500:
                raise errors.NotFoundError(kind='region', identifier=region_id)
        elif region_name is not None:
            return self._single_search('region', region_name)
        elif constellation_id is not None:
            constellation_response = self._base_constellation(constellation_id)
            constellation_info = constellation_response.json()
            return self.get_region(region_id=constellation_info[u'region_id'])
        elif constellation_name is not None:
            constellation_info = self.get_constellation(
                constellation_name=constellation_name)
            constellation_id = constellation_info[u'id']
            return self.get_region(constellation_id=constellation_id)
        elif system_id is not None:
            system_response = self._base_system(system_id)
            system_info = system_response.json()
            constellation_id = system_info[u'constellation_id']
            return self.get_region(constellation_id=constellation_id)
        elif system_name is not None:
            system_info = self.get_system(system_name=system_name)
            system_id = system_info[u'id']
            return self.get_region(system_id=system_id)
        else:
            raise TypeError("Need at least a region's, constellation's, or "
                            "system's name or ID to look up.")


    def get_constellation(self, constellation_name=None, constellation_id=None,
                          system_name=None, system_id=None):
        if constellation_id is not None:
            constellation_response = self._base_constellation(constellation_id)
            constellation_info = constellation_response.json()
            return {
                u'name': constellation_info[u'name'],
                u'id': constellation_id,
            }
        elif constellation_name is not None:
            return self._single_search('constellation', constellation_name)
        elif system_id is not None:
            system_response = self._base_system(system_id)
            system_info = system_response.json()
            constellation_id = system_info[u'constellation_id']
            return self.get_constellation(constellation_id=constellation_id)
        elif system_name is not None:
            system_info = self.get_system(system_name=system_name)
            system_id = system_info[u'id']
            return self.get_constellation(system_id=system_id)
        else:
            raise TypeError("Need at least a constellation's or system's "
                             "name or ID to look up.")

    def get_system(self, system_name=None, system_id=None):
        if system_id is not None:
            system_response = self._base_system(system_id)
            system_info = system_response.json()
            return {
                u'name': system_info[u'name'],
                u'id': system_id,
            }
        elif system_name is not None:
            return self._single_search('solarsystem', system_name)
        else:
            raise TypeError("Need at least a system's name or ID to look up.")

    def _base_corporation(self, corporation_id):
        resp = self._esi_request('v3', '/corporations/{corporation_id}/',
                                 corporation_id=corporation_id)
        if resp.status_code == 404:
            raise errors.NotFoundError(kind='corporation',
                                       identifier=corporation_id)
        elif resp.status_code == 500:
            raise errors.EsiError(resp)
        return resp

    def _base_character(self, character_id):
        resp = self._esi_request('v4', '/characters/{character_id}/',
                                 character_id=character_id)
        if resp.status_code == 404:
            raise errors.NotFoundError(kind='character',
                                       identifier=character_id)
        elif resp.status_code == 500:
            raise errors.EsiError(resp)
        return resp

    def get_alliance(self, alliance_name=None, alliance_id=None,
                     corporation_name=None, corporation_id=None,
                     character_name=None, character_id=None):
        if alliance_id is not None:
            alliance_response = self._esi_request('v2',
                                                  '/alliances/{alliance_id}/',
                                                  alliance_id=alliance_id)
            if alliance_response.status_code == 200:
                alliance_info = alliance_response.json()
                return {
                    u'name': alliance_info[u'alliance_name'],
                    u'id': alliance_id,
                }
            elif alliance_response.status_code == 404:
                raise errors.NotFoundError('alliance', alliance_id)
            else:
                raise errors.EsiError(alliance_response)
        elif alliance_name is not None:
            return self._single_search('alliance', alliance_name)
        elif corporation_id is not None:
            corp_response = self._base_corporation(corporation_id)
            corp_info = corp_response.json()
            if u'alliance_id' not in corp_info:
                raise errors.NotInAllianceError('corporation', corporation_id)
            return self.get_alliance(alliance_id=corp_info['alliance_id'])
        elif corporation_name is not None:
            corp_info = self.get_corporation(corporation_name=corporation_name)
            return self.get_alliance(corporation_id=corp_info[u'id'])
        elif character_id is not None:
            character_response = self._base_character(character_id)
            character_info = character_response.json()
            if u'alliance_id' not in character_info:
                raise errors.NotInAllianceError('character', character_id)
            return self.get_alliance(
                alliance_id=character_info[u'alliance_id'])
        elif character_name is not None:
            character_info = self.get_ccp_character(
                character_name=character_name)
            return self.get_alliance(character_id=character_info[u'id'])
        else:
            raise TypeError("Need at least an alliance's, corporation's, or "
                             "character's name or id to look up.")

    def get_corporation(self, corporation_name=None, corporation_id=None,
                        character_name=None, character_id=None):
        if corporation_id is not None:
            corp_response = self._base_corporation(corporation_id)
            corp_info = corp_response.json()
            return {
                u'name': corp_info[u'corporation_name'],
                u'id': corporation_id,
            }
        elif corporation_name is not None:
            return self._single_search('corporation', corporation_name)
        elif character_id is not None:
            character_response = self._base_character(character_id)
            character_info = character_response.json()
            corp_id = character_info[u'corporation_id']
            return self.get_corporation(corporation_id=corp_id)
        elif character_name is not None:
            character_info = self.get_ccp_character(
                character_name=character_name)
            return self.get_corporation(character_id=character_info[u'id'])
        else:
            raise TypeError("Need at least a corporation's or "
                             "character's name or id to look up.")

    def get_ccp_character(self, character_name=None, character_id=None):
        if character_id is not None:
            character_response = self._base_character(character_id)
            character_info = character_response.json()
            return {
                u'name': character_info[u'name'],
                u'id': character_id,
            }
        elif character_name is not None:
            return self._single_search('character', character_name)
        else:
            raise TypeError("Need at least a character's name or id to "
                             "look up.")

    def get_type(self, type_name=None, type_id=None):
        if type_id is not None:
            type_response = self._esi_request('v2',
                                              '/universe/types/{type_id}/',
                                              type_id=type_id)
            if type_response.status_code == 200:
                type_info = type_response.json()
                return {
                    u'id': type_id,
                    u'name': type_info[u'name'],
                }
            elif type_response.status_code == 404:
                raise errors.NotFoundError('type', type_id)
            else:
                raise errors.EsiError(type_response)
        elif type_name is not None:
            search_response = self._esi_request('v1', 'search', strict=True,
                                                categories=['inventorytype'],
                                                search=type_name)
            search_json = search_response.json()
            # It is possible for there to be multiple types for a single name.
            # A good example is the query 'Cruor' will return two results.
            type_ids = search_json.get(u'inventorytype', [])
            if len(type_ids) == 0:
                raise errors.NotFoundError('type', type_name)
            elif len(type_ids) == 1:
                return {
                    u'name': type_name,
                    u'id': type_ids[0],
                }
            else:
                for type_id in type_ids:
                    type_response = self._esi_request('v2', ('/universe/types'
                                                             '/{type_id}/'),
                                                      type_id=type_id)
                    type_info = type_response.json()
                    if type_info[u'published']:
                        return {
                            u'name': type_name,
                            u'id': type_id,
                        }
                # If none are published, return the first one
                return {
                    u'name': type_name,
                    u'id': type_ids[0],
                }
        else:
            raise TypeError("Need at least a type's name or ID to look up.")


class CachingCcpStore(CcpStore):

    @staticmethod
    def _update_map(static_map, getter, **kwargs):
        if len(kwargs) != 1:
            raise TypeError("Too many keyword arguments given to _update_map")
        key, value = kwargs.popitem()
        kwargs[key] = value
        if key.endswith('_name'):
            working_map = {v: k for k, v in six.iteritems(static_map)}
        elif key.endswith('_id'):
            working_map = static_map
        else:
            raise TypeError("Incorrect keyword argument given to _update_map")
        try:
            if key.endswith('_id'):
                id_ = value
                name = working_map[value]
            elif key.endswith('_name'):
                id_ = working_map[value]
                name = value
        except KeyError:
            info = getter(**kwargs)
            id_ = info[u'id']
            name = info[u'name']
            static_map[id_] = name
        return {
            u'id': id_,
            u'name': name,
        }

    @staticmethod
    def _location_kwarg(caller_level, **kwargs):
        # get_region has a priority of *_id over *_name and region_* >
        # constellation_* > system_*. We're using **kwargs to make super
        # calling easier, but we need to still respect the argument priority.
        # get_constellation and get_system methods just drop region and both
        # region and constellation respectively.
        if caller_level not in ('region', 'constellation', 'system'):
            raise ValueError("caller_level must be 'region', 'constellation' "
                             "or 'system'.")
        key_priorities = ('region_id', 'region_name', 'constellation_id',
                          'constellation_name', 'system_id', 'system_name')
        # filter out invalid keys

        def filter_higher(k):
            # This is using the first letter of the keywords to see if they are
            # region, constellation or system keys. For region-level lookups,
            # all keys are valid, for constellation-level, only constellation
            # and system, and system-level allows only the system keys.
            if caller_level[0] == 'c':
                return k[0] in ('c', 's')
            elif caller_level[0] == 's':
                return k[0] == 's'
            else:
                return True
        valid_keys = filter(filter_higher, key_priorities)
        for priority in valid_keys:
            if priority in kwargs:
                key = priority
                value = kwargs[key]
                return key, value
        if caller_level == 'region':
            needed = "region's, constelletion's, or system's"
        elif caller_level == 'constelletion':
            needed = "constelletion's or system's"
        else:
            needed = "system's"
        msg = "Need at least a {} name or ID to look up.".format(needed)
        raise TypeError(msg)

    def get_region(self, **kwargs):
        key, value = self._location_kwarg('region', **kwargs)

        if key.startswith('region_'):
            getter = super(CachingCcpStore, self).get_region
            return self._update_map(static_data.region_names, getter, **kwargs)
        elif key == 'constellation_id':
            if value not in static_data.constellations_to_regions:
                super_info = super(CachingCcpStore, self).get_region(**kwargs)
                region_id = super_info[u'id']
                static_data.constellations_to_regions[value] = region_id
            else:
                region_id = static_data.constellations_to_regions[value]
            return self.get_region(region_id=region_id)
        else:
            # For all other keys, we just want the constellation ID. Use
            # get_constellation to figure that out.
            constellation_info = self.get_constellation(**kwargs)
            constellation_id = constellation_info[u'id']
            return self.get_region(constellation_id=constellation_id)

    def get_constellation(self, **kwargs):
        key, value = self._location_kwarg('constellation', **kwargs)
        if key.startswith('constellation_'):
            getter = super(CachingCcpStore, self).get_constellation
            return self._update_map(static_data.constellation_names, getter,
                                    **kwargs)
        elif key == 'system_id':
            if value not in static_data.systems_to_constellations:
                super_info = super(CachingCcpStore, self).get_constellation(
                    **kwargs)
                constellation_id = super_info[u'id']
                static_data.systems_to_constellations[value] = constellation_id
            else:
                constellation_id = static_data.systems_to_constellations[value]
            return self.get_constellation(constellation_id=constellation_id)
        elif key == 'system_name':
            system_info = self.get_system(**kwargs)
            system_id = system_info[u'id']
            return self.get_constellation(system_id=system_id)

    def get_system(self, **kwargs):
        key, value = self._location_kwarg('system', **kwargs)
        getter = super(CachingCcpStore, self).get_system
        return self._update_map(static_data.system_names, getter, **kwargs)

    def get_type(self, **kwargs):
        key_priorities = ('type_id', 'type_name')
        for priority in key_priorities:
            if priority in kwargs:
                key = priority
                value = kwargs[key]
                break
        # for-else isn't very common in Python. If you're unfamiliar, the else
        # block executes if the loop does *not* break.
        else:
            raise TypeError("Need at least a type's name or ID to look up.")
        kwargs = {key: value}
        getter = super(CachingCcpStore, self).get_type
        return self._update_map(static_data.ships, getter, **kwargs)
