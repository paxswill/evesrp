"""Allow Pilots to not have owning users.

Revision ID: e6b2c156b11
Revises: 8f179e969c9
Create Date: 2014-09-03 17:13:17.282827

"""

# revision identifiers, used by Alembic.
revision = 'e6b2c156b11'
down_revision = '8f179e969c9'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    op.alter_column('pilot', 'user_id', existing_type=sa.Integer,
            nullable=True)


def downgrade():
    op.alter_column('pilot', 'user_id', existing_type=sa.Integer,
            nullable=False)
