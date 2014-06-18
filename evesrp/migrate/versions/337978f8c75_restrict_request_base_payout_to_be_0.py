"""Restrict request.base_payout to be >= 0

Revision ID: 337978f8c75
Revises: c1fc69b629
Create Date: 2014-06-18 14:04:52.963890

"""

# revision identifiers, used by Alembic.
revision = '337978f8c75'
down_revision = 'c1fc69b629'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import update, select, table, column


request = table('request',
        column('id', sa.Integer),
        column('base_payout', sa.Float),
)


def upgrade():
    conn = op.get_bind()
    negative_base_payout_id_sel = select([request.c.id])\
            .where(request.c.base_payout < 0.0)
    negative_ids = conn.execute(negative_base_payout_id_sel)
    for result_row in negative_ids:
        negative_id = result_row[0]
        update_stmt = update(request)\
                .where(request.c.id == negative_id)\
                .values({
                        'base_payout': 0.0,
                })
        conn.execute(update_stmt)
    negative_ids.close()


def downgrade():
    # This is a lossy upgrade, no downgrading possible
    pass
