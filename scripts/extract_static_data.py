#!/usr/bin/env python
"""Script to update the static data packaged with the app."""

from __future__ import unicode_literals, print_function, division

import pprint
import sys
import time
import requests
from requests.adapters import HTTPAdapter
import cachecontrol


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
                        # Sometimes CREST flipsout and closes the connection.
                        # Give it some alone time and things usually start
                        # working.
                        print("\tBig sleep #{}".format(attempt_num + 1))
                        time.sleep(2)
                    else:
                        break
                else:
                    raise Exception
                self.cache[request.url] = response
                return self.cache[request.url]


session = requests.Session()
# Actual limit is supposed to be 150/sec, but 140 gives a nice safety cushion.
session.mount('https://', RateLimitedCache(requests_per_second=140))
session.headers.update(
        {'User-Agent': 'EVE-SRPStaticDataUpdater/1.0 (paxswill@paxswill.com'})


CREST_ROOT = 'https://public-crest.eveonline.com/'


def system_names():
    crest_root = session.get(CREST_ROOT).json()
    crest_systems = session.get(crest_root['systems']['href']).json()
    return {s['id']: s['name'] for s in crest_systems['items']}


def constellation_names():
    crest_root = session.get(CREST_ROOT).json()
    crest_constellations = session.get(
            crest_root['constellations']['href']).json()
    return {s['id']: s['name'] for s in crest_constellations['items']}


def region_names():
    crest_root = session.get(CREST_ROOT).json()
    crest_regions = session.get(crest_root['regions']['href']).json()
    return {s['id']: s['name'] for s in crest_regions['items']}


def ship_names():
    crest_root = session.get(CREST_ROOT).json()
    categories = session.get(crest_root['itemCategories']['href']).json()
    ships_category = None
    for category in categories['items']:
        if category['name'] == 'Ship':
            ships_category = session.get(category['href']).json()
            break
    ships = {}
    for group_href in [g['href'] for g in ships_category['groups']]:
        group = session.get(group_href).json()
        def get_typeid(type_info):
            # It'd be nice if the group info had the type ID instead of just
            # the href and the name so I didn't have to parse the href.
            split_href = type_info['href'].rsplit('/', 2)
            if split_href[-1] == '':
                return int(split_href[-2])
            else:
                return int(split_href[-1])
        ships.update({get_typeid(t): t['name'] for t in group['types']})
    return ships


def get_relations():
    crest_root = session.get(CREST_ROOT).json()
    regions = session.get(crest_root['regions']['href']).json()
    systems_to_constellations = {}
    constellations_to_regions = {}
    for region_href in [r['href'] for r in regions['items']]:
        region = session.get(region_href).json()
        for constellation_info in region['constellations']:
            constellations_to_regions[constellation_info['id']] =\
                    region['id']
            constellation = session.get(constellation_info['href']).json()
            for system_info in constellation['systems']:
                systems_to_constellations[system_info['id']] =\
                        constellation_info['id']
    return systems_to_constellations, constellations_to_regions


def write_static_data(path):
    with open(path, 'w') as f:
        f.write("# coding: utf-8")
        f.write("from __future__ import unicode_literals\n\n")
        printer = pprint.PrettyPrinter(indent=3, stream=f)
        print("Writing ships...", end="", flush=True)
        f.write("ships = ")
        printer.pprint(ship_names())
        print("done", flush=True)
        print("Writing system names...", end="", flush=True)
        f.write("\nsystem_names = ")
        printer.pprint(system_names())
        print("done", flush=True)
        print("Writing constellation names...", end="", flush=True)
        f.write("\nconstellation_names = ")
        printer.pprint(constellation_names())
        print("done", flush=True)
        print("Writing region names...", end="", flush=True)
        f.write("\nregion_names = ")
        printer.pprint(region_names())
        print("done", flush=True)
        print("Writing relations...", end="", flush=True)
        sys2con, con2reg = get_relations()
        f.write("\nsystems_to_constellations = ")
        printer.pprint(sys2con)
        f.write("\nconstellations_to_regions = ")
        printer.pprint(con2reg)
        print("done", flush=True)


if __name__ == '__main__':
    try:
        output_name = sys.argv[2]
    except IndexError:
        output_name = 'static_data.py'
    print("This script can take ~10 minutes to run, so leave it be for a"
          "while.")
    write_static_data(output_name)
