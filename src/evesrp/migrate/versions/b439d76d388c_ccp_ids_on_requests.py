from __future__ import print_function

"""Use CCP ID to refer to things on Requests

Things include locations (system, region, constellation), corps, alliances, and
types.

Revision ID: b439d76d388c
Revises: 3f453bb4f2d7
Create Date: 2016-05-25 21:06:27.198237

"""

# revision identifiers, used by Alembic.
revision = 'b439d76d388c'
down_revision = '3f453bb4f2d7'

import datetime as dt
import json
from alembic import op, context
import six
import sqlalchemy as sa
from sqlalchemy.sql import update, select, table, column, join, outerjoin, \
                           bindparam
from evesrp.migrate import process_request_ids as pri


request = table('request',
                column('id', sa.Integer),
                column('corporation', sa.String(150)),
                column('corporation_id', sa.Integer),
                column('alliance', sa.String(150)),
                column('alliance_id', sa.Integer),
                column('ship_type', sa.String(75)),
                column('type_id', sa.Integer),
                column('system', sa.String(25)),
                column('system_id', sa.Integer),
                column('constellation', sa.String(25)),
                column('constellation_id', sa.Integer),
                column('region', sa.String(25)),
                column('region_id', sa.Integer),
                column('kill_timestamp', sa.DateTime),
                column('killmail_url', sa.String(512))
)

transformers = table('transformerref',
                     column('attribute_name', sa.String(50))
)


def create_temp_table(request_ids, bind):
    metadata = sa.MetaData(bind=bind)
    temp_request_ids = sa.Table('temp_request_ids', metadata,
        sa.Column('request_id', sa.Integer(), nullable=False),
        prefixes=['TEMPORARY']
    )
    temp_request_ids.create(bind=bind)
    insert_data = [{'request_id': int(r_id)} for r_id in request_ids]
    bind.execute(temp_request_ids.insert(), insert_data)
    return temp_request_ids


def upgrade():
    # Get all the data ready to go before we modify the DB. Ideally
    # transactions would obviate the need for this, but the MySQL Alembic
    # driver defaults to non-transactional.
    # Look for pre-processed data with the -x flag
    try:
        x_args = context.get_x_argument(as_dictionary=True)
        app = pri.SRPApp(data_path=x_args.get('requestids',
                                              'srp_requests.json'))
    except (AttributeError, KeyError):
        # If there's no -x argument given, there will be an AttributeError
        # In either that case or a missing 'data' key, set the preloaded data
        # dictionary to be empty
        app = pri.SRPApp()
    # Get a connection to the DB
    bind = op.get_bind()
    # Load already processed request IDs into a temporary table
    temp_table = create_temp_table(app.requests_data.keys(), bind)
    # Get all unmigrated request IDs
    request_sel = select([request.c.id, request.c.corporation,
                          request.c.alliance, request.c.ship_type,
                          request.c.system, request.c.constellation,
                          request.c.region, request.c.killmail_url,
                          request.c.kill_timestamp])
    request_sel = request_sel.select_from(request.outerjoin(temp_table,
        temp_table.c.request_id == request.c.id))
    request_sel = request_sel.where(temp_table.c.request_id == None)
    requests = bind.execute(request_sel)
    # Find the IDs for corp, alliance, ship, system, constellation and region
    # for those requests.
    try:
        for request_num, request_info in enumerate(requests):
            app_format = dict(request_info)
            app_format['ship'] = app_format['ship_type']
            # turn the timestamp into a string so the migration tool can parse
            # it back into a datetime object again.
            app_format['kill_timestamp'] = \
                request_info['kill_timestamp'].isoformat()
            request_data = app._migrate_request(app_format)
            app.requests_data[request_info['id']] = request_data
            if request_num % 10 == 0:
                app.save()
    except (ValueError, LookupError, AttributeError,
            AssertionError, TypeError, KeyboardInterrupt) as e:
        print("Saving data processed so far...")
        app.save()
        print("...done. Re-use this data by passing in an -x parameter")
        raise
    # If we reached here without erroring out, it's succeeded. But save just in
    # case.
    app.save()
    # Add new columns without not-null constraints
    op.add_column('request',
                  sa.Column('corporation_id', sa.Integer(), nullable=True))
    op.add_column('request',
                  sa.Column('alliance_id', sa.Integer(), nullable=True))
    op.add_column('request',
                  sa.Column('type_id', sa.Integer(), nullable=True))
    op.add_column('request',
                  sa.Column('system_id', sa.Integer(), nullable=True))
    op.add_column('request',
                  sa.Column('constellation_id', sa.Integer(), nullable=True))
    op.add_column('request',
                  sa.Column('region_id', sa.Integer(), nullable=True))
    # Update with the new data
    # Account for the case where you have information about requests that are
    # not present in your database.
    request_ids = bind.execute(select([request.c.id]))

    def update_format(request_id):
        data = dict(request_id=request_id)
        data.update(app.requests_data[request_id])
        return data

    update_data = [update_format(row['id']) for row in request_ids]
    update_data = list(update_data)
    up = update(request).where(request.c.id == bindparam('request_id',
                                                         type_=sa.Integer))
    bind.execute(up, update_data)
    # Enable not-null constraints
    op.alter_column('request', 'corporation_id', nullable=False,
                    existing_type=sa.Integer())
    # Skip alliance_id, it *is* allowed to be null
    op.alter_column('request', 'type_id', nullable=False,
                    existing_type=sa.Integer())
    op.alter_column('request', 'system_id', nullable=False,
                    existing_type=sa.Integer())
    op.alter_column('request', 'constellation_id', nullable=False,
                    existing_type=sa.Integer())
    op.alter_column('request', 'region_id', nullable=False,
                    existing_type=sa.Integer())
    # Rename the 'ship' column to 'type_name'
    op.drop_index('ix_request_ship_type', 'request')
    op.alter_column('request', 'ship_type', new_column_name='type_name',
                    existing_type=sa.String(150), existing_nullable=False)
    op.create_index('ix_request_type_name', 'request', ['type_name'],
                    unique=False)
    # Migrate any transformers on ship_type
    op.execute(update(transformers).\
               where(transformers.c.attribute_name == 'ship_type').\
               values(attribute_name='type_name'))



def downgrade():
    # Drop new columns
    op.drop_column('request', 'type_id')
    op.drop_column('request', 'system_id')
    op.drop_column('request', 'region_id')
    op.drop_column('request', 'corporation_id')
    op.drop_column('request', 'constellation_id')
    op.drop_column('request', 'alliance_id')
    # Rename 'type_' to 'ship'
    op.drop_index('ix_request_type_name', 'request')
    op.alter_column('request', 'type_name', new_column_name='ship_type',
                    existing_type=sa.String(150), existing_nullable=False)
    op.create_index('ix_request_ship_type', 'request', ['ship_type'],
                    unique=False)
    # Update tranformers
    op.execute(update(transformers).\
               where(transformers.c.attribute_name == 'type_name').\
               values(attribute_name='ship_type'))
