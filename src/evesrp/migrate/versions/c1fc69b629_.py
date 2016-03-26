"""Change to a division-specified transformer for ships and pilots.

Revision ID: c1fc69b629
Revises: 2f22504b1e6
Create Date: 2014-05-07 15:10:10.404234

"""

# revision identifiers, used by Alembic.
revision = 'c1fc69b629'
down_revision = '2f22504b1e6'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('division',
            sa.Column('pilot_transformer', sa.PickleType(), nullable=True))
    op.add_column('division',
            sa.Column('ship_transformer', sa.PickleType(), nullable=True))
    op.drop_column('request', 'ship_url')


def downgrade():
    op.add_column('request',
            sa.Column('ship_url', sa.VARCHAR(length=500), nullable=True))
    op.drop_column('division', 'ship_transformer')
    op.drop_column('division', 'pilot_transformer')
