"""Split modifier types out into classes.

Revision ID: 2976d59f286
Revises: 4198a248c8a
Create Date: 2014-06-18 15:19:55.611649

"""

# revision identifiers, used by Alembic.
revision = '2976d59f286'
down_revision = '4198a248c8a'

from decimal import Decimal
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import update, select, table, column


modifier = table('modifier',
        column('id', sa.Integer),
        column('value', sa.Float),
        column('type_', sa.Enum('absolute', 'percentage',
                name='modifier_type')),
        column('_type', sa.String(length=20)),
)


abs_table = table('absolute_modifier',
        column('id', sa.Integer),
        column('value', sa.Numeric(precision=15, scale=2)))


rel_table = table('relative_modifier',
        column('id', sa.Integer),
        column('value', sa.Float))


def upgrade():
    # Add discriminator column
    op.add_column('modifier', sa.Column('_type', sa.String(length=20)))
    # Create new subclass tables
    op.create_table('absolute_modifier',
            sa.Column('id', sa.Integer,
                    sa.ForeignKey('modifier.id'),
                    primary_key=True),
            sa.Column('value', sa.Numeric(precision=15, scale=2),
                    nullable=False, server_default='0.0'))
    op.create_table('relative_modifier',
            sa.Column('id', sa.Integer, sa.ForeignKey('modifier.id'),
                    primary_key=True),
            sa.Column('value', sa.Float, nullable=False, server_default='0.0'))
    # Add new entries to the subclass tables for each modifier
    conn = op.get_bind()
    modifier_sel = select([modifier.c.id, modifier.c.value, modifier.c.type_])
    modifiers = conn.execute(modifier_sel)
    absolutes = []
    relatives = []
    for modifier_id, modifier_value, modifier_type in modifiers:
        if modifier_type == 'absolute':
            discriminator = 'AbsoluteModifier'
            absolutes.append({
                    'id': modifier_id,
                    'value': Decimal.from_float(modifier_value) * 1000000,
            })
        elif modifier_type == 'percentage':
            discriminator = 'RelativeModifier'
            relatives.append({
                    'id': modifier_id,
                    'value': modifier_value / 100,
            })
        update_stmt = update(modifier)\
                .where(modifier.c.id == modifier_id)\
                .values({
                        '_type': discriminator,
                })
        conn.execute(update_stmt)
    modifiers.close()
    op.bulk_insert(abs_table, absolutes)
    op.bulk_insert(rel_table, relatives)
    # Drop the old value and type_ columns from modifier
    op.drop_column('modifier', 'value')
    op.drop_column('modifier', 'type_')
    # Add the not-null constraint to the _type column
    op.alter_column('modifier',
            column_name='_type',
            nullable=True,
            existing_type=sa.String(length=20),
    )


def downgrade():
    # Add type_ and value columns back
    op.add_column('modifier',
            sa.Column('type_', sa.Enum('absolute', 'percentage',
                    name='modifier_type')))
    op.add_column('modifier', sa.Column('value', sa.Float, nullable=True))
    # populate type_ and value columns with data from the subclass tables
    abs_select = select([abs_table.c.id, abs_table.c.value])
    rel_select = select([rel_table.c.id, rel_table.c.value])
    conn = op.get_bind()
    for select_stmt in (abs_select, rel_select):
        modifier_rows = conn.execute(select_stmt)
        for modifier_id, modifier_value in modifier_rows:
            if select_stmt == abs_select:
                modifier_value = float(modifier_value / 1000000)
                type_ = 'absolute'
            else:
                type_ = 'percentage'
            update_stmt = update(modifier)\
                    .where(modifier.c.id == modifier_id)\
                    .values({
                        'value': modifier_value,
                        'type_': type_
                    })
            conn.execute(update_stmt)
        modifier_rows.close()
    # Drop the old _type column and the subclass tables
    op.drop_column('modifier', '_type')
    op.drop_table('absolute_modifier')
    op.drop_table('relative_modifier')
    # Add not-null constraint back to type_
    op.alter_column('modifier',
            column_name='type_',
            nullable=False,
            existing_type=sa.Enum('absolute', 'percentage',
                    name='modifier_type'))
