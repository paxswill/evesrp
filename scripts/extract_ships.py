#!/usr/bin/env python

"""Script for generating a Python file with a variable 'ships' containing a
dictionary of all of the ships in Eve.
"""

from pprint import PrettyPrinter
from sys import argv
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.sql import select


engine = create_engine(argv[1])
metadata = MetaData(bind=engine)


invTypes = Table('invTypes', metadata, autoload=True)


invMarketGroups = Table('invMarketGroups', metadata, autoload=True)


def get_group_types(group_id, conn):
    sel = select([invTypes.c.typeID])
    sel = sel.where(invTypes.c.marketGroupID == group_id)
    result = conn.execute(sel)
    type_ids = set(map(lambda x: x[0], result))
    result.close()
    return type_ids


def walk_groups(group_id, conn):
    type_ids = set()
    # if there're items in here, get the first
    sel = select([invMarketGroups.c.hasTypes])
    sel = sel.where(invMarketGroups.c.marketGroupID == group_id)
    sel = sel.limit(1)
    result = conn.execute(sel)
    row = result.fetchone()
    result.close()
    if row[0] == 1:
        sel = select([invTypes.c.typeID])
        sel = sel.where(invTypes.c.marketGroupID == group_id)
        result = conn.execute(sel)
        type_ids.update(map(lambda x: x[0], result))
        result.close()
    # get subgroups
    sel = select([invMarketGroups.c.marketGroupID])
    sel = sel.where(invMarketGroups.c.parentGroupID == group_id)
    # Recurse into subgroups to find their IDs
    result = conn.execute(sel)
    for row in result:
        type_ids.update(walk_groups(row[0], conn))
    result.close()
    return type_ids


def find_ship_ids(conn):
    # Construct query to find the root ship market group
    sel = select([invMarketGroups.c.marketGroupID])
    sel = sel.where(invMarketGroups.c.marketGroupName == 'Ships')
    sel = sel.where(invMarketGroups.c.parentGroupID == None)
    sel = sel.limit(1)
    result = conn.execute(sel)
    row = result.fetchone()
    result.close()
    # And now we recurse
    return walk_groups(row[0], conn)


def map_names(conn, type_ids):
    ship_names = {}
    base_sel = select([invTypes.c.typeName])
    for type_id in type_ids:
        sel = base_sel.where(invTypes.c.typeID == type_id).limit(1)
        result = conn.execute(sel)
        row = result.fetchone()
        ship_names[type_id] = row[0]
        result.close()
    return ship_names


if __name__ == '__main__':
    conn = engine.connect()
    ship_ids = find_ship_ids(conn)
    names = map_names(conn, ship_ids)
    conn.close()
    try:
        output_name = argv[2]
    except IndexError:
        output_name = 'ships.py'
    with open(output_name, 'w') as f:
        f.write("ships = ")
        printer = PrettyPrinter(indent=4, stream=f)
        printer.pprint(names)
