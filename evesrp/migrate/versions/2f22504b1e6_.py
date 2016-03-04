"""Add location attributes to Request.

Revision ID: 2f22504b1e6
Revises: None
Create Date: 2014-05-02 13:24:00.045482

"""

# revision identifiers, used by Alembic.
revision = '2f22504b1e6'
down_revision = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import update, select, table, column
import requests
from time import sleep
from evesrp import systems


session = requests.Session()


def get_system_id(kill_id):
    # Have to put a sleep in here to prevent hammering the server and getting
    # banned
    sleep(10)
    resp = session.get(
            'https://zkb.pleaseignore.com/api/no-attackers/no-items/killID/{}'
            .format(kill_id))
    if resp.status_code == 200:
        return int(resp.json()[0]['solarSystemID'])
    else:
        print(resp.text)
        return None


request = table('request',
        column('id', sa.Integer),
        column('system', sa.String(25)),
        column('constellation', sa.String(25)),
        column('region', sa.String(25)),
)


def upgrade():
    # Add columns, but with null allowed
    op.add_column('request', sa.Column('constellation', sa.String(length=25),
            nullable=True))
    op.add_column('request', sa.Column('region', sa.String(length=25),
            nullable=True))
    op.add_column('request', sa.Column('system', sa.String(length=25),
            nullable=True))
    op.create_index('ix_request_constellation', 'request', ['constellation'],
            unique=False)
    op.create_index('ix_request_region', 'request', ['region'], unique=False)
    op.create_index('ix_request_system', 'request', ['system'], unique=False)
    # Update existing requests
    conn = op.get_bind()
    kill_id_sel = select([request.c.id])
    kill_ids = conn.execute(kill_id_sel)
    for kill_id in kill_ids:
        kill_id = kill_id[0]
        system_id = get_system_id(kill_id)
        system = systems.system_names[system_id]
        constellation = systems.systems_constellations[system]
        region = systems.constellations_regions[constellation]
        update_stmt = update(request)\
                .where(request.c.id==op.inline_literal(kill_id))\
                .values({
                    'system': system,
                    'constellation': constellation,
                    'region': region,
                })
        conn.execute(update_stmt)
    kill_ids.close()
    # Add non-null constraint
    op.alter_column('request', 'constellation', nullable=False,
            existing_server_default=None,
            existing_type=sa.String(length=25))
    op.alter_column('request', 'region', nullable=False,
            existing_server_default=None,
            existing_type=sa.String(length=25))
    op.alter_column('request', 'system', nullable=False,
            existing_server_default=None,
            existing_type=sa.String(length=25))



def downgrade():
    op.drop_index('ix_request_system', table_name='request')
    op.drop_index('ix_request_region', table_name='request')
    op.drop_index('ix_request_constellation', table_name='request')
    op.drop_column('request', 'system')
    op.drop_column('request', 'region')
    op.drop_column('request', 'constellation')
