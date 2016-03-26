"""Add a Full Text Search index for MySQL

Revision ID: 19506187e7aa
Revises: 108d7a5881c7
Create Date: 2014-07-23 11:32:21.748067

"""

# revision identifiers, used by Alembic.
revision = '19506187e7aa'
down_revision = '108d7a5881c7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        op.execute('CREATE FULLTEXT INDEX ix_request_details_fulltext ON '
                   'request (details);')


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        op.drop_index('ix_request_details_fulltext', 'details')
