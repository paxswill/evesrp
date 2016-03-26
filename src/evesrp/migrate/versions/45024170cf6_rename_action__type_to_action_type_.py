"""Rename action._type to action.type_

Revision ID: 45024170cf6
Revises: 337978f8c75
Create Date: 2014-06-18 14:21:37.202030

"""

# revision identifiers, used by Alembic.
revision = '45024170cf6'
down_revision = '337978f8c75'

from alembic import op
import sqlalchemy as sa
from evesrp.models import ActionType


def upgrade():
    op.alter_column('action',
            column_name='_type',
            new_column_name='type_',
            existing_type=ActionType.db_type,
            existing_nullable=False)


def downgrade():
    op.alter_column('action',
            column_name='type_',
            new_column_name='_type',
            existing_type=ActionType.db_type,
            existing_nullable=False)
