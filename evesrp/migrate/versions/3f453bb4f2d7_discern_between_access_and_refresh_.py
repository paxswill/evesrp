"""Discern between access and refresh tokens for OAuth

Revision ID: 3f453bb4f2d7
Revises: e6b2c156b11
Create Date: 2016-02-04 15:58:56.096867

"""

# revision identifiers, used by Alembic.
revision = '3f453bb4f2d7'
down_revision = 'e6b2c156b11'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # Inspect the current database to see if we're using OAuth
    metadata = sa.MetaData(bind=op.get_bind())
    metadata.reflect()
    table_names = {t.name for t in metadata.sorted_tables}
    if 'o_auth_user' in table_names:
        op.add_column('o_auth_user',
                sa.Column('access_expiration',
                    sa.DateTime(),
                    nullable=True))
        op.add_column('o_auth_user',
                sa.Column('refresh_token',
                    sa.String(length=100, convert_unicode=True),
                    nullable=True))
        op.alter_column('o_auth_user', 'token', new_column_name='access_token',
                existing_type=sa.String(length=100, convert_unicode=True),
                existing_nullable=True)


def downgrade():
    # Inspect the current database to see if we're using OAuth
    metadata = sa.MetaData(bind=op.get_bind())
    metadata.reflect()
    table_names = {t.name for t in metadata.sorted_tables}
    if 'o_auth_user' in table_names:
        op.drop_column('o_auth_user', 'refresh_token')
        op.drop_column('o_auth_user', 'access_expiration')
        op.alter_column('o_auth_user', 'access_token', new_column_name='token',
                existing_type=sa.String(length=100, convert_unicode=True),
                existing_nullable=True)
