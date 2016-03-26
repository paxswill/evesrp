"""Move from using floats for ISK to numeric types.

Revision ID: 4198a248c8a
Revises: 45024170cf6
Create Date: 2014-06-18 14:34:25.967159

"""

# revision identifiers, used by Alembic.
revision = '4198a248c8a'
down_revision = '45024170cf6'

from decimal import Decimal
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import update, select, table, column


def upgrade():
    op.add_column('request',
            sa.Column('numeric_base_payout', sa.Numeric(precision=15, scale=2),
                    default=0.0)
    )
    request = table('request',
            column('id', sa.Integer),
            column('base_payout', sa.Float),
            column('numeric_base_payout', sa.Numeric(precision=15, scale=2)),
    )
    conn = op.get_bind()
    requests_sel = select([request.c.id, request.c.base_payout])
    requests = conn.execute(requests_sel)
    for request_id, float_payout in requests:
        decimal_payout = Decimal.from_float(float_payout)
        decimal_payout *= 1000000
        update_stmt = update(request)\
                .where(request.c.id == request_id)\
                .values({
                    'numeric_base_payout': decimal_payout,
                })
        conn.execute(update_stmt)
    requests.close()
    op.drop_column('request', 'base_payout')
    op.alter_column('request',
            column_name='numeric_base_payout',
            new_column_name='base_payout',
            existing_type=sa.Numeric(precision=15, scale=2),
            existing_server_default=0.0)


def downgrade():
    op.add_column('request',
            sa.Column('float_base_payout', sa.Float, default=0.0)
    )
    request = table('request',
            column('id', sa.Integer),
            column('base_payout', sa.Numeric(precision=15, scale=2)),
            column('float_base_payout', sa.Float),
    )
    conn = op.get_bind()
    requests_sel = select([request.c.id, request.c.base_payout])
    requests = conn.execute(requests_sel)
    for request_id, decimal_payout in requests:
        decimal_payout = decimal_payout / 1000000
        float_payout = float(decimal_payout)
        update_stmt = update(request)\
                .where(request.c.id == request_id)\
                .values({
                    'float_base_payout': float_payout,
                })
        conn.execute(update_stmt)
    requests.close()
    op.drop_column('request', 'base_payout')
    op.alter_column('request',
            column_name='numeric_base_payout',
            new_column_name='base_payout',
            existing_type=sa.Float,
            existing_server_default=0.0)
