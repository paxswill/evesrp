#!/usr/bin/env python

from __future__ import unicode_literals

"""Script for generating a Python file with variables mapping solar systems to
constellations and regions. It also has mappings between the IDs for those
items and their names.
"""

from pprint import PrettyPrinter
from sys import argv
import os
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.sql import select


engine = create_engine(argv[1])
metadata = MetaData(bind=engine)


mapSystems = Table('mapSolarSystems', metadata, autoload=True)
mapConstellations = Table('mapConstellations', metadata, autoload=True)
mapRegions = Table('mapRegions', metadata, autoload=True)


if __name__ == '__main__':
    conn = engine.connect()

    systemNames = {}
    sel = select([mapSystems.c.solarSystemID, mapSystems.c.solarSystemName])
    result = conn.execute(sel)
    for row in result:
        systemNames[row[0]] = row[1]
    result.close()

    constellationNames = {}
    sel = select([mapConstellations.c.constellationID,
            mapConstellations.c.constellationName])
    result = conn.execute(sel)
    for row in result:
        constellationNames[row[0]] = row[1]
    result.close()

    regionNames = {}
    sel = select([mapRegions.c.regionID, mapRegions.c.regionName])
    result = conn.execute(sel)
    for row in result:
        regionNames[row[0]] = row[1]
    result.close()

    systemConstellations = {}
    sel = select([mapSystems.c.solarSystemName,
            mapSystems.c.constellationID])
    result = conn.execute(sel)
    for row in result:
        systemConstellations[row[0]] = constellationNames[row[1]]
    result.close()

    constellationRegions = {}
    sel = select([mapConstellations.c.constellationName,
            mapConstellations.c.regionID])
    result = conn.execute(sel)
    for row in result:
        constellationRegions[row[0]] = regionNames[row[1]]
    result.close()

    conn.close()

    # Write the file
    try:
        output_name = argv[2]
    except IndexError:
        output_name = 'systems.py'
    with open(output_name, 'w') as f:
        f.write("system_names = ")
        printer = PrettyPrinter(indent=4, stream=f)
        printer.pprint(systemNames)
        f.write("\nconstellation_names = ")
        printer.pprint(constellationNames)
        f.write("\nregion_names = ")
        printer.pprint(regionNames)
        f.write("\nsystems_constellations = ")
        printer.pprint(systemConstellations)
        f.write("\nconstellations_regions = ")
        printer.pprint(constellationRegions)
