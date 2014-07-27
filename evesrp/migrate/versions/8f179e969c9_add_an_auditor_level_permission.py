"""Add an auditor-level permission, and fix Enum item order

Revision ID: 8f179e969c9
Revises: 5795c29b2c7a
Create Date: 2014-07-24 17:24:12.026685

"""

# revision identifiers, used by Alembic.
revision = '8f179e969c9'
down_revision = '3e5e1d3a02c'

from alembic import op
import sqlalchemy as sa


new_enum = sa.Enum(u'admin', u'audit', u'review', u'pay', u'submit',
        convert_unicode=True,
        name=u'ck_permission_type')


old_enum = sa.Enum(u'admin', u'review', u'pay', u'submit',
        convert_unicode=True,
        name=u'ck_permission_type')


def upgrade():
    op.alter_column('permission', 'permission', type_=new_enum,
            existing_type=old_enum, existing_nullable=False)


def downgrade():
    op.alter_column('permission', 'permission', type_=old_enum,
            existing_type=new_enum, existing_nullable=False)
