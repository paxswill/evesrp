"""Add API key table

Revision ID: 3d35f833a24
Revises: 4280bf2417c
Create Date: 2014-06-25 03:30:29.351874

"""

# revision identifiers, used by Alembic.
revision = '3d35f833a24'
down_revision = '4280bf2417c'

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add the table for API keys
    op.create_table('apikey',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('timestamp', sa.DateTime, nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('key', sa.LargeBinary(length=32), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['user.id']),
            sa.PrimaryKeyConstraint('id'))


def downgrade():
    op.drop_table('apikey')
