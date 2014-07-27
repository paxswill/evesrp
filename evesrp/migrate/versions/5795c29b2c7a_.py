"""Change RelativeModifier.value to a Numeric/Decimal

Revision ID: 5795c29b2c7a
Revises: 19506187e7aa
Create Date: 2014-07-23 14:43:45.748696

"""

# revision identifiers, used by Alembic.
revision = '5795c29b2c7a'
down_revision = '19506187e7aa'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import update, select, table, column
from decimal import Decimal


def upgrade():
    relative_modifier = table('relative_modifier',
            column('id', sa.Integer),
            column('value', sa.Float),
            column('numeric_value', sa.Numeric(precision=8, scale=5)))
    op.add_column('relative_modifier',
            sa.Column('numeric_value', sa.Numeric(precision=8, scale=5)))
    conn = op.get_bind()
    sel = select([relative_modifier.c.id, relative_modifier.c.value])
    results = conn.execute(sel)
    q = Decimal(10) ** -5
    for id_, float_value in results:
        decimal_value = Decimal(float_value).quantize(q)
        up = update(relative_modifier).where(relative_modifier.c.id == id_)\
                .values({'numeric_value': decimal_value})
        conn.execute(up)
    op.drop_column('relative_modifier', 'value')
    op.alter_column('relative_modifier', 'numeric_value', nullable=True,
            new_column_name='value', existing_type=sa.Numeric(precision=8,
                    scale=5))


def downgrade():
    relative_modifier = table('relative_modifier',
            column('id', sa.Integer),
            column('value', sa.Numeric(precision=8, scale=5)),
            column('float_value', sa.Float))
    op.add_column('relative_modifier', sa.Column('float_value', sa.Float))
    conn = op.get_bind()
    sel = select([relative_modifier.c.id, relative_modifier.c.value])
    results = conn.execute(sel)
    for id_, decimal_value in results:
        float_value = float(decimal_value)
        up = update(relative_modifier).where(relative_modifier.c.id == id_)\
                .values({'float_value': float_value})
        conn.execute(up)
    op.drop_column('relative_modifier', 'value')
    op.alter_column('relative_modifier', 'float_value', nullable=True,
            new_column_name='value', existing_type=sa.Float)
