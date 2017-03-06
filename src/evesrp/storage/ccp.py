try:
    from collections.abc import Sequence
except ImportError:
    from collections import Sequence
import json

import requests
import six

from evesrp import static_data


class CcpStore(object):

    def __init__(self, requests_session=None):
        if requests_session is None:
            requests_session = requests.Session()
        self.session = requests_session

    def _esi_request(self, version, path, _method='GET', **params):
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
        resp = self.session.request(_method,
                                    parameter_url,
                                    params=query_params)
        results = {
            u'_debug': {
                u'source': u'esi',
                u'url': resp.url,
                u'http_code': resp.status_code,
            },
        }
        try:
            results[u'result'] = resp.json()
        except ValueError:
            results[u'error'] = u"Response not parseable"
        if 'Warning' in resp.headers:
            results[u'warning'] = resp.headers['warning']
        return results

    def _single_search(self, category, query):
        results = self._esi_request('v1', 'search', strict=True,
                                 categories=[category], search=query)
        # Slightly massage the data
        raw_result = results[u'result'][category]
        if raw_result is None:
            # Not found
            results[u'result'] = None
        if len(raw_result) == 1:
            results[u'result'] = raw_result[0]
        else:
            # Multiple results, like if there's a name with a '.' at the end.
            # This means we get to go through and find the right ID
            name_lookup = getattr(self, 'get_{}_name'.format(category))
            for result_id in raw_result:
                name_results = name_lookup(result_id)
                if name_results[u'result'] == query:
                    results[u'result'] = result_id
        return results

    def get_region_id(self, name):
        return self._single_search('region', name)

    def get_region_name(self, ccp_id):
        resp = self._esi_request('v1', '/universe/regions/{region_id}/',
                                 region_id=ccp_id)
        resp[u'result'] = resp[u'result'][u'name']
        return resp

    def get_constellation_id(self, name):
        return self._single_search('constellation', name)

    def get_constellation_name(self, ccp_id):
        resp = self._esi_request('v1',
                                 '/universe/constellations/{constellation_id}/',
                                 constellation_id=ccp_id)
        resp[u'result'] = resp[u'result'][u'name']
        return resp

    def get_system_id(self, name):
        return self._single_search('solarsystem', name)

    def get_system_name(self, ccp_id):
        resp = self._esi_request('v2', '/universe/systems/{system_id}/',
                                 system_id=ccp_id)
        resp[u'result'] = resp[u'result'][u'name']
        return resp

    def get_character_id(self, name):
        # Same with corporations, ESI only considers the current holder of a
        # name, not past names (ex: a name was freed up when CCP cleared
        # out names someimte around 2013 or 2014. I now have the name, and only
        # my character is returned).
        return self._single_search('character', name)

    def get_character_name(self, ccp_id):
        resp = self._esi_request('v4', '/characters/{character_id}/',
                                 character_id=ccp_id)
        resp[u'result'] = resp[u'result'][u'name']
        return resp

    def get_corporation_id(self, corporation_name=None, character_name=None,
                           character_id=None):
        # Note, ESI only returns active corporations (at least as of
        # 2017-02-15), so we don't have to deal with duplicates.
        if corporation_name is not None:
            return self._single_search('corporation', corporation_name)
        if character_name is not None:
            character_id = self.get_character_id(character_name)[u'result']
        if character_id is not None:
            resp = self._esi_request('v4', '/characters/{character_id}/',
                                     character_id=character_id)
            resp[u'result'] = resp[u'result'][u'corporation_id']
            return resp
        raise ValueError

    def get_corporation_name(self, ccp_id):
        resp = self._esi_request('v3', '/corporations/{corporation_id}/',
                                 corporation_id=ccp_id)
        resp[u'result'] = resp[u'result'][u'corporation_name']
        return resp

    def get_alliance_id(self, alliance_name=None, corporation_name=None,
                        corporation_id=None):
        if alliance_name is not None:
            return self._single_search('alliance', alliance_name)
        if corporation_name is not None and corporation_id is None:
            id_results = self.get_corporation_id(corporation_name)
            corporation_id = id_results[u'result']
        if corporation_id is not None:
            resp = self._esi_request('v3', '/corporations/{corporation_id}/',
                                     corporation_id=corporation_id)
            resp[u'result'] = resp[u'result'][u'alliance_id']
            return resp
        raise ValueError

    def get_alliance_name(self, ccp_id):
        resp = self._esi_request('v2', '/alliances/{alliance_id}/',
                                 alliance_id=ccp_id)
        resp[u'result'] = resp[u'result'][u'alliance_name']
        return resp

    def get_type_id(self, name):
        # it is possible for there to be multiple types for a single name. A
        # good example is the query 'Cruor' will return two results.
        results = self._esi_request('v1', 'search', strict=True,
                                 categories=['inventorytype'], search=name)
        type_ids = results[u'result'][u'inventorytype']
        if len(type_ids) == 1:
            results[u'result'] = type_ids[0]
        else:
            for type_id in type_ids:
                type_result = self._esi_request('v2',
                                                '/universe/types/{type_id}/',
                                                type_id=type_id)
                if type_result[u'result'][u'published']:
                    results[u'result'] = result
                    return results
            # If none are published, return the first one
            results[u'result'] = type_ids[0]
        return results

    def get_type_name(self, ccp_id):
        resp = self._esi_request('v2', '/universe/types/{type_id}/',
                                 type_id=ccp_id)
        resp[u'result'] = resp[u'result'][u'name']
        return resp


class CachingCcpStore(CcpStore):

    def _try_flipped_static_map(self, static_map, name, getter_name):
        flipped = {v: k for k, v in six.iteritems(static_map)}
        try:
            return {
                u'result': flipped[name],
                u'_debug': {
                    u'source': u'static_data',
                },
            }
        except KeyError:
            result = getattr(super(CachingCcpStore, self), getter_name)(name)
            if result[u'result'] is not None:
                static_map[result[u'result']] = name
                result.get(u'_debug', {})[u'cache_status'] = u'added'
            return result

    def _try_static_map(self, static_map, ccp_id, getter_name):
        try:
            return {
                u'result': static_map[ccp_id],
                u'_debug': {
                    u'source': u'static_data',
                },
            }
        except KeyError:
            result = getattr(super(CachingCcpStore, self), getter_name)(ccp_id)
            static_map[ccp_id] = result[u'result']
            result.get(u'_debug', {})[u'cache_status'] = u'added'
            return result

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
