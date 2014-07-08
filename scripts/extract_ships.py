#!/usr/bin/env python

from __future__ import unicode_literals

"""Script for generating a Python file with a variable 'ships' containing a
dictionary of all of the ships in Eve.
"""

from pprint import PrettyPrinter
from sys import argv
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.sql import select


engine = create_engine(argv[1])
metadata = MetaData(bind=engine)


invCategories = Table('invCategories', metadata, autoload=True)
invGroups = Table('invGroups', metadata, autoload=True)
invTypes = Table('invTypes', metadata, autoload=True)


if __name__ == '__main__':
    conn = engine.connect()

    # Get the Ship category ID
    cat_sel = select([invCategories.c.categoryID]).\
            where(invCategories.c.categoryName == 'Ship').limit(1)
    result = conn.execute(cat_sel)
    cat_id = result.fetchone()[0]
    result.close()

    # Get groups in this category
    group_sel = select([invGroups.c.groupID]).where(
            invGroups.c.categoryID == cat_id)
    group_result = conn.execute(group_sel)

    # get typeIDs and names
    names = {}
    for group_row in group_result:
        group_id = group_row[0]
        type_sel = select([invTypes.c.typeID, invTypes.c.typeName]).\
                where(invTypes.c.groupID == group_id)
        type_result = conn.execute(type_sel)
        for row in type_result:
            names[row[0]] = row[1]
        type_result.close()

    # Cleanup
    group_result.close()
    conn.close()

    # Write the file
    try:
        output_name = argv[2]
    except IndexError:
        output_name = 'ships.py'
    with open(output_name, 'w') as f:
        f.write("ships = ")
        printer = PrettyPrinter(indent=4, stream=f)
        printer.pprint(names)
