try:
    from collections.abc import Sequence
except ImportError:
    from collections import Sequence

import requests
import six

from evesrp import static_data


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
        results = {
            u'http_code': resp.status_code,
            u'_debug': {
                u'source': u'esi',
                u'url': resp.url,
            },
        }
        if resp.status_code == 200:
            try:
                results[u'result'] = resp.json()
            except ValueError:
                # There's no other chance for errors to be set or not before
                # this. Set it uncondtionally.
                results[u'errors'] = [u"Response not parseable."]
        else:
            results[u'result'] = None
        if 'Warning' in resp.headers:
            # As above, no other chance that warnings was set before now.
            results[u'warnings'] = [resp.headers['warning']]
        if resp.status_code == 500:
            # errors could have been set earlier, so play it safe from now on
            results.setdefault(u'errors', [])
            results[u'errors'].append(u"Internal Server Error.")
        return results

    def _single_search(self, category, query):
        search_results = self._esi_request('v1', 'search', strict=True,
                                           categories=[category], search=query)
        if category not in search_results[u'result']:
            # Not found
            search_results[u'result'] = None
            search_results.setdefault(u'errors', [])
            search_results[u'errors'].append(
                u"{} named '{}' not found.".format(
                    category.capitalize(), query))
        elif len(search_results[u'result'][category]) == 1:
            # Single result
            search_results[u'result'] = {
                u'name': query,
                u'id': search_results[u'result'][category][0],
            }
        else:
            # Multiple results
            # This can happen if the query string is a substring of the other
            # results. Because we're only searching for full names, this can
            # happen if there's a dot at the end or things like that. Because
            # we're also searching for exact matches, we then just look up all
            # the names for the IDs and figure it out from there
            result_ids = search_results[u'result'][category]
            names_resp = self._esi_request('v2', 'universe/names/',
                                           method='POST',
                                           json_data=result_ids)
            # the category names used in /universe/names/ are different than
            # /search/
            if category == 'inventorytype':
                names_category = 'inventory_type'
            elif category == 'solar_system':
                names_category = 'solar_system'
            else:
                names_category = category
            # Find the matching name
            for name_result in names_resp[u'result']:
                if name_result[u'category'] == names_category and \
                        name_result[u'name'] == query:
                    search_results[u'result'] = {
                        u'id': name_result[u'id'],
                        u'name': query,
                    }
                    break
            else:
                msg = ("ESI /search/ returned IDs that /universe/names/ can't "
                       "resolve ({}).").format(", ".join(result_ids))
                raise ValueError(msg)
        return search_results

    def _base_constellation(self, constellation_id):
        esi_path = '/universe/constellations/{constellation_id}/'
        resp = self._esi_request('v1', esi_path,
                                 constellation_id=constellation_id)
        # NOTE As of 2017-03-07, ESI returns 500 instead of 404 for
        # constellations not found. Github issue ccpgames/esi-issues#307
        # When this is fixed, change back to checking for 404, stop
        # clearing the server error message from the results, and stop setting
        # the status code to 404 for all 500 errors.
        if resp[u'http_code'] == 500:
            if resp.get(u'errors') == [u"Internal Server Error."]:
                resp[u'errors'] = []
            resp[u'http_code'] = 404
            # End ESI workaround
            resp[u'result'] = None
            resp.setdefault(u'errors', [])
            resp[u'errors'].append((u"Constellation {} Not Found.").format(
                constellation_id))
        return resp

    def _base_system(self, system_id):
        resp = self._esi_request('v2', '/universe/systems/{system_id}/',
                                 system_id=system_id)
        # NOTE As of 2017-03-07, ESI returns 500 instead of 404 for systems
        # not found. Github issue ccpgames/esi-issues#307
        # When this is fixed, change back to checking for 404 and stop
        # clearing the server error message from the results and setting the
        # code to 404 on all 500s.
        if resp[u'http_code'] == 500:
            if resp.get(u'errors') == [u"Internal Server Error."]:
                resp[u'errors'] = []
            resp[u'http_code'] = 404
            # End ESI workaround
            resp[u'result'] = None
            resp.setdefault(u'errors', [])
            resp[u'errors'].append(u"System {} Not Found.".format(system_id))
        return resp

    @staticmethod
    def _merge_sub_result(parent_result, sub_result):
        for key in (u'warnings', u'errors'):
            if key in sub_result:
                parent_result.setdefault(key, [])
                parent_result[key].extend(sub_result[key])
        return parent_result

    def get_region(self, region_name=None, region_id=None,
                   constellation_name=None, constellation_id=None,
                   system_name=None, system_id=None):
        if region_id is not None:
            resp = self._esi_request('v1', '/universe/regions/{region_id}/',
                                     region_id=region_id)
            if resp[u'http_code'] == 200:
                resp[u'result'] = {
                    u'name': resp[u'result'][u'name'],
                    u'id': region_id,
                }
            # NOTE As of 2017-03-07, ESI returns 500 instead of 404 for regions
            # not found. Github issue ccpgames/esi-issues#307
            # When this is fixed, change back to checking for 404 and stop
            # clearing the server error message from the results
            elif resp[u'http_code'] == 500:
                if resp.get(u'errors') == [u"Internal Server Error."]:
                    resp[u'errors'] = []
                resp[u'result'] = None
                resp.setdefault(u'errors', [])
                resp[u'errors'].append(u"Region {} Not Found.".format(
                    region_id))
            return resp
        elif region_name is not None:
            return self._single_search('region', region_name)
        elif constellation_id is not None:
            constellation_result = self._base_constellation(constellation_id)
            if constellation_result[u'result'] is None:
                return constellation_result
            region_result = self.get_region(
                region_id=constellation_result[u'result'][u'region_id'])
            return self._merge_sub_result(region_result, constellation_result)
        elif constellation_name is not None:
            constellation_resp = self.get_constellation(
                constellation_name=constellation_name)
            if constellation_resp[u'result'] is None:
                return constellation_resp
            constellation_id = constellation_resp[u'result']['id']
            region_resp = self.get_region(constellation_id=constellation_id)
            return self._merge_sub_result(region_resp, constellation_resp)
        elif system_id is not None:
            system_resp = self._base_system(system_id)
            if system_resp[u'result'] is None:
                return system_resp
            constellation_id = system_resp[u'result'][u'constellation_id']
            region_resp = self.get_region(constellation_id=constellation_id)
            return self._merge_sub_result(region_resp, system_resp)
        elif system_name is not None:
            system_resp = self.get_system(system_name=system_name)
            if system_resp[u'result'] is None:
                return system_resp
            system_id = system_resp[u'result'][u'id']
            region_resp = self.get_region(system_id=system_id)
            return self._merge_sub_result(region_resp, system_resp)
        else:
            raise ValueError("Need at least a region's, constellation's, or "
                             "system's name or ID to look up.")


    def get_constellation(self, constellation_name=None, constellation_id=None,
                          system_name=None, system_id=None):
        if constellation_id is not None:
            resp = self._base_constellation(constellation_id)
            if resp[u'http_code'] == 200:
                resp[u'result'] = {
                    u'name': resp[u'result'][u'name'],
                    u'id': constellation_id,
                }
            elif resp[u'http_code'] == 404:
                resp[u'result'] = None
                resp.setdefault(u'errors', [])
                resp[u'errors'].append(u"Constellation {} Not Found.".format(
                    constellation_id))
            return resp
        elif constellation_name is not None:
            return self._single_search('constellation', constellation_name)
        elif system_id is not None:
            system_resp = self._base_system(system_id)
            if system_resp[u'result'] is None:
                return system_resp
            constellation_id = system_resp[u'result'][u'constellation_id']
            constellation_resp = self.get_constellation(
                constellation_id=constellation_id)
            return self._merge_sub_result(constellation_resp, system_resp)
        elif system_name is not None:
            system_resp = self.get_system(system_name=system_name)
            if system_resp[u'result'] is None:
                return system_resp
            system_id = system_resp[u'result'][u'id']
            constellation_resp = self.get_constellation(system_id=system_id)
            return self._merge_sub_result(constellation_resp, system_resp)
        else:
            raise ValueError("Need at least a constellation's or system's "
                             "name or ID to look up.")

    def get_system(self, system_name=None, system_id=None):
        if system_id is not None:
            resp = self._base_system(system_id)
            if resp[u'http_code'] == 200:
                resp[u'result'] = {
                    u'name': resp[u'result'][u'name'],
                    u'id': system_id,
                }
            elif resp[u'http_code'] == 404:
                resp[u'result'] = None
                resp.setdefault(u'errors', [])
                resp[u'errors'].append(u"System {} Not Found.".format(
                    system_id))
            return resp
        elif system_name is not None:
            return self._single_search('solarsystem', system_name)
        else:
            raise ValueError("Need at least a system's name or ID to look up.")

    def _base_corporation(self, corporation_id):
        resp = self._esi_request('v3', '/corporations/{corporation_id}/',
                                 corporation_id=corporation_id)
        if resp[u'http_code'] == 404:
            resp[u'result'] = None
            resp.setdefault(u'errors', [])
            resp[u'errors'].append(u"Corporation {} Not Found.".format(
                corporation_id))
        return resp

    def _base_character(self, character_id):
        resp = self._esi_request('v4', '/characters/{character_id}/',
                                 character_id=character_id)
        if resp[u'http_code'] == 404:
            resp[u'result'] = None
            resp.setdefault(u'errors', [])
            resp[u'errors'].append(u"Character {} Not Found.".format(
                character_id))
        return resp

    def get_alliance(self, alliance_name=None, alliance_id=None,
                     corporation_name=None, corporation_id=None,
                     character_name=None, character_id=None):
        if alliance_id is not None:
            resp = self._esi_request('v2', '/alliances/{alliance_id}/',
                                     alliance_id=alliance_id)
            if resp[u'http_code'] == 200:
                resp[u'result'] = {
                    u'name': resp[u'result'][u'alliance_name'],
                    u'id': alliance_id,
                }
            elif resp[u'http_code'] == 404:
                resp[u'result'] = None
                resp.setdefault(u'errors', [])
                resp[u'errors'].append(u"Alliance {} Not Found.".format(
                    alliance_id))
            return resp
        elif alliance_name is not None:
            return self._single_search('alliance', alliance_name)
        elif corporation_id is not None:
            corp_resp = self._base_corporation(corporation_id)
            if corp_resp[u'result'] is None:
                return corp_resp
            if u'alliance_id' not in corp_resp[u'result']:
                corp_resp[u'result'] = None
                corp_resp.setdefault(u'errors', [])
                corp_resp[u'errors'].append(
                    u"Corporation {} is not in an alliance.".format(
                        corporation_id))
                return corp_resp
            alliance_resp = self.get_alliance(
                alliance_id=corp_resp[u'result']['alliance_id'])
            return self._merge_sub_result(alliance_resp, corp_resp)
        elif corporation_name is not None:
            corp_resp = self.get_corporation(corporation_name=corporation_name)
            if corp_resp[u'result'] is None:
                return corp_resp
            alliance_resp = self.get_alliance(
                corporation_id=corp_resp[u'result'][u'id'])
            return self._merge_sub_result(alliance_resp, corp_resp)
        elif character_id is not None:
            char_resp = self._base_character(character_id)
            if char_resp[u'result'] is None:
                return char_resp
            if u'alliance_id' not in char_resp[u'result']:
                char_resp[u'result'] = None
                char_resp.setdefault(u'errors', [])
                char_resp[u'errors'].append(
                    u"Character {} is not in an alliance.".format(
                        character_id))
                return char_resp
            alliance_resp = self.get_alliance(
                alliance_id=char_resp[u'result'][u'alliance_id'])
            return self._merge_sub_result(alliance_resp, char_resp)
        elif character_name is not None:
            char_resp = self.get_ccp_character(character_name=character_name)
            if char_resp[u'result'] is None:
                return char_resp
            alliance_resp = self.get_alliance(
                character_id=char_resp[u'result'][u'id'])
            return self._merge_sub_result(alliance_resp, char_resp)
        else:
            raise ValueError("Need at least an alliance's, corporation's, or "
                             "character's name or id to look up.")

    def get_corporation(self, corporation_name=None, corporation_id=None,
                        character_name=None, character_id=None):
        if corporation_id is not None:
            resp = self._base_corporation(corporation_id)
            if resp[u'http_code'] == 200:
                resp[u'result'] = {
                    u'name': resp[u'result'][u'corporation_name'],
                    u'id': corporation_id,
                }
            elif resp[u'http_code'] == 404:
                resp[u'result'] = None
                resp.setdefault(u'errors', [])
                resp[u'errors'].append(u"Corporation {} Not Found.".format(
                    corporation_id))
            return resp
        elif corporation_name is not None:
            return self._single_search('corporation', corporation_name)
        elif character_id is not None:
            char_resp = self._base_character(character_id)
            if char_resp[u'result'] is None:
                return char_resp
            corp_id = char_resp[u'result'][u'corporation_id']
            corp_resp = self.get_corporation(corporation_id=corp_id)
            return self._merge_sub_result(corp_resp, char_resp)
        elif character_name is not None:
            char_resp = self.get_ccp_character(character_name=character_name)
            if char_resp[u'result'] is None:
                return char_resp
            corp_resp = self.get_corporation(
                character_id=char_resp[u'result'][u'id'])
            return self._merge_sub_result(corp_resp, char_resp)
        else:
            raise ValueError("Need at least a corporation's or "
                             "character's name or id to look up.")

    def get_ccp_character(self, character_name=None, character_id=None):
        if character_id is not None:
            resp = self._base_character(character_id)
            if resp[u'http_code'] == 200:
                resp[u'result'] = {
                    u'name': resp[u'result'][u'name'],
                    u'id': character_id,
                }
            elif resp[u'http_code'] == 404:
                resp[u'result'] = None
                resp.setdefault(u'errors', [])
                resp[u'errors'].append(u"Character {} Not Found.".format(
                    character_id))
            return resp
        elif character_name is not None:
            return self._single_search('character', character_name)
        else:
            raise ValueError("Need at least a character's name or id to "
                             "look up.")

    def get_type(self, type_name=None, type_id=None):
        if type_id is not None:
            resp = self._esi_request('v2', '/universe/types/{type_id}/',
                                     type_id=type_id)
            if resp[u'http_code'] == 200:
                resp[u'result'] = {
                    u'id': type_id,
                    u'name': resp[u'result'][u'name'],
                }
            elif resp[u'http_code'] == 404:
                resp[u'result'] = None
                resp.setdefault(u'errors', [])
                resp[u'errors'].append(u"Type {} Not Found.".format(type_id))
            return resp
        elif type_name is not None:
            results = self._esi_request('v1', 'search', strict=True,
                                        categories=['inventorytype'],
                                        search=type_name)
            # It is possible for there to be multiple types for a single name.
            # A good example is the query 'Cruor' will return two results.
            type_ids = results[u'result'].get(u'inventorytype', [])
            if len(type_ids) == 0:
                results[u'result'] = None
                results.setdefault(u'errors', [])
                results[u'errors'].append(u"Type {} Not Found.".format(
                    type_name))
            elif len(type_ids) == 1:
                results[u'result'] = {
                    u'name': type_name,
                    u'id': type_ids[0],
                }
            else:
                for type_id in type_ids:
                    type_result = self._esi_request('v2',
                                                    ('/universe/types'
                                                     '/{type_id}/'),
                                                    type_id=type_id)
                    if type_result[u'result'][u'published']:
                        results[u'result'] = {
                            u'name': type_name,
                            u'id': type_id,
                        }
                        return results
                # If none are published, return the first one
                results[u'result'] = {
                    u'name': type_name,
                    u'id': type_ids[0],
                }
            return results
        else:
            raise ValueError("Need at least a type's name or ID to look up.")


class CachingCcpStore(CcpStore):

    @staticmethod
    def _update_map(static_map, getter, **kwargs):
        if len(kwargs) != 1:
            raise ValueError("Too many keyword arguments given to _update_map")
        key, value = kwargs.popitem()
        kwargs[key] = value
        if key.endswith('_name'):
            working_map = {v: k for k, v in six.iteritems(static_map)}
        elif key.endswith('_id'):
            working_map = static_map
        else:
            raise ValueError("Incorrect keyword argument given to _update_map")
        try:
            if key.endswith('_id'):
                id_ = value
                name = working_map[value]
            elif key.endswith('_name'):
                id_ = working_map[value]
                name = value
        except KeyError:
            resp = getter(**kwargs)
            if resp[u'result'] is None:
                return resp
            id_ = resp[u'result'][u'id']
            name = resp[u'result'][u'name']
            static_map[id_] = name
        return {
            u'result': {
                u'id': id_,
                u'name': name,
            },
            u'_debug': {
                u'source': u'static_data',
            },
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
        raise ValueError(msg)

    def get_region(self, **kwargs):
        key, value = self._location_kwarg('region', **kwargs)

        if key.startswith('region_'):
            getter = super(CachingCcpStore, self).get_region
            return self._update_map(static_data.region_names, getter, **kwargs)
        elif key == 'constellation_id':
            if value not in static_data.constellations_to_regions:
                super_resp = super(CachingCcpStore, self).get_region(**kwargs)
                if super_resp[u'result'] is None:
                    return super_resp
                region_id = super_resp[u'result'][u'id']
                static_data.constellations_to_regions[value] = region_id
            else:
                region_id = static_data.constellations_to_regions[value]
            return self.get_region(region_id=region_id)
        else:
            # For all other keys, we just want the constellation ID. Use
            # get_constellation to figure that out.
            constellation_resp = self.get_constellation(**kwargs)
            if constellation_resp[u'result'] is None:
                return constellation_resp
            constellation_id = constellation_resp[u'result'][u'id']
            return self.get_region(constellation_id=constellation_id)

    def get_constellation(self, **kwargs):
        key, value = self._location_kwarg('constellation', **kwargs)
        if key.startswith('constellation_'):
            getter = super(CachingCcpStore, self).get_constellation
            return self._update_map(static_data.constellation_names, getter,
                                    **kwargs)
        elif key == 'system_id':
            if value not in static_data.systems_to_constellations:
                super_resp = super(CachingCcpStore, self).get_constellation(
                    **kwargs)
                if super_resp[u'result'] is None:
                    return super_resp
                constellation_id = super_resp[u'result'][u'id']
                static_data.systems_to_constellations[value] = constellation_id
            else:
                constellation_id = static_data.systems_to_constellations[value]
            return self.get_constellation(constellation_id=constellation_id)
        elif key == 'system_name':
            system_resp = self.get_system(**kwargs)
            if system_resp[u'result'] is None:
                return system_resp
            system_id = system_resp[u'result'][u'id']
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
            raise ValueError("Need at least a type's name or ID to look up.")
        kwargs = {key: value}
        getter = super(CachingCcpStore, self).get_type
        return self._update_map(static_data.ships, getter, **kwargs)
