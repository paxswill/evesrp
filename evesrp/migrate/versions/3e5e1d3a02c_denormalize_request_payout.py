"""Denormalize Request.payout

Revision ID: 3e5e1d3a02c
Revises: 5795c29b2c7a
Create Date: 2014-07-26 21:25:29.870535

"""

# revision identifiers, used by Alembic.
revision = '3e5e1d3a02c'
down_revision = '5795c29b2c7a'

from decimal import Decimal
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import update, select, table, column, join, outerjoin, case
from sqlalchemy.sql.functions import func


request = table('request',
        column('id', sa.Integer),
        column('base_payout', sa.Numeric(precision=15, scale=2)),
        column('payout', sa.Numeric(precision=15, scale=2)))


mod_table = table('modifier',
        column('id', sa.Integer),
        column('request_id', sa.Integer),
        column('_type', sa.String(length=20)),
        column('voided_user_id', sa.Integer))


abs_table = table('absolute_modifier',
        column('id', sa.Integer),
        column('value', sa.Numeric(precision=15, scale=2)))


rel_table = table('relative_modifier',
        column('id', sa.Integer),
        column('value', sa.Numeric(precision=8, scale=5)))


def upgrade():
    op.add_column('request',
            sa.Column('payout', sa.Numeric(precision=15, scale=2), index=True,
                nullable=True))

    bind = op.get_bind()
    absolute = select([abs_table.c.value.label('value'),
                       mod_table.c.request_id.label('request_id')])\
            .select_from(join(abs_table, mod_table,
                    mod_table.c.id == abs_table.c.id))\
            .where(mod_table.c.voided_user_id == None)\
            .alias()
    relative = select([rel_table.c.value.label('value'),
                       mod_table.c.request_id.label('request_id')])\
            .select_from(join(rel_table, mod_table,
                    mod_table.c.id == rel_table.c.id))\
            .where(mod_table.c.voided_user_id == None)\
            .alias()
    abs_sum = select([request.c.id.label('request_id'),
                      request.c.base_payout.label('base_payout'),
                      func.sum(absolute.c.value).label('sum')])\
            .select_from(outerjoin(request, absolute,
                    request.c.id == absolute.c.request_id))\
            .group_by(request.c.id)\
            .alias()
    rel_sum = select([request.c.id.label('request_id'),
                      func.sum(relative.c.value).label('sum')])\
            .select_from(outerjoin(request, relative,
                    request.c.id == relative.c.request_id))\
            .group_by(request.c.id)\
            .alias()
    total_sum = select([abs_sum.c.request_id.label('request_id'),
                        ((
                            abs_sum.c.base_payout +
                            case([(abs_sum.c.sum == None, Decimal(0))],
                                    else_=abs_sum.c.sum)) *
                         (
                            1 +
                            case([(rel_sum.c.sum == None, Decimal(0))],
                                    else_=rel_sum.c.sum))).label('payout')])\
            .select_from(join(abs_sum, rel_sum,
                    abs_sum.c.request_id == rel_sum.c.request_id))
    payouts = bind.execute(total_sum)
    for request_id, payout in payouts:
        up = update(request).where(request.c.id == request_id).values(
                payout=payout)
        bind.execute(up)
    op.alter_column('request', 'payout', nullable=False,
            existing_type=sa.Numeric(precision=15, scale=2))


def downgrade():
    op.drop_column('request', 'payout')
