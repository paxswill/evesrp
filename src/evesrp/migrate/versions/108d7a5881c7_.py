"""Name constraints and indicies in a common manner across databases.

Revision ID: 108d7a5881c7
Revises: 3d35f833a24
Create Date: 2014-07-22 13:19:50.598892

"""

# revision identifiers, used by Alembic.
revision = '108d7a5881c7'
down_revision = '3d35f833a24'

from alembic import op
import sqlalchemy as sa
import six
from itertools import groupby


fkeys = {
    ('absolute_modifier', 'id'): ('modifier', 'id'),
    ('action', 'request_id'): ('request', 'id'),
    ('action', 'user_id'): ('user', 'id'),
    ('apikey', 'user_id'): ('user', 'id'),
    ('core_group', 'id'): ('group', 'id'),
    ('core_user', 'id'): ('user', 'id'),
    ('group', 'id'): ('entity', 'id'),
    ('modifier', 'request_id'): ('request', 'id'),
    ('modifier', 'user_id'): ('user', 'id'),
    ('modifier', 'voided_user_id'): ('user', 'id'),
    ('note', 'user_id'): ('user', 'id'),
    ('note', 'noter_id'): ('user', 'id'),
    ('permission', 'division_id'): ('division', 'id'),
    ('permission', 'entity_id'): ('entity', 'id'),
    ('pilot', 'user_id'): ('user', 'id'),
    ('relative_modifier', 'id'): ('modifier', 'id'),
    ('request', 'submitter_id'): ('user', 'id'),
    ('request', 'division_id'): ('division', 'id'),
    ('request', 'pilot_id'): ('pilot', 'id'),
    ('test_group', 'id'): ('group', 'id'),
    ('test_user', 'id'): ('user', 'id'),
    ('transformerref', 'division_id'): ('division', 'id'),
    ('user', 'id'): ('entity', 'id'),
    ('users_groups', 'user_id'): ('user', 'id'),
    ('users_groups', 'group_id'): ('group', 'id'),
}

pkeys = {
    'absolute_modifier': ['id'],
    'action': ['id'],
    'apikey': ['id'],
    'core_group': ['id'],
    'core_user': ['id'],
    'division': ['id'],
    'entity': ['id'],
    'group': ['id'],
    'modifier': ['id'],
    'note': ['id'],
    'permission': ['id'],
    'pilot': ['id'],
    'relative_modifier': ['id'],
    'request': ['id'],
    'test_group': ['id'],
    'test_user': ['id'],
    'transformerref': ['id'],
    'user': ['id'],
}

uniq = {
    'permission': ('division_id', 'entity_id', 'permission'),
    'transformerref': ('division_id', 'attribute_name'),
}


naming_schemes = {
    'standard': {
        'foreignkey': ('fk_{local_table}_{local_col}_{remote_table}'
                       '_{remote_col}'),
        'primary': 'pk_{table_name}',
        'unique': 'uq_{table_name}_{columns[0]}',
    },
    'mysql': {
        'foreignkey': '{local_table}_ibfk_{table_num}',
        'primary': 'PRIMARY',
        'unique': '{columns[0]}',
    },
    'postgresql': {
        'foreignkey': '{local_table}_{local_col}_fkey',
        'primary': '{table_name}_pkey',
        'unique': None,
    },
}


def prune_tablenames():
    # Skip tables that aren't present in the target database, like specific
    # AuthMethods that aren't enabled.
    metadata = sa.MetaData(bind=op.get_bind())
    metadata.reflect()
    tables = {t.name for t in metadata.sorted_tables}
    for table_col in list(six.iterkeys(fkeys)):
        if table_col[0] not in tables:
            del fkeys[table_col]
    for table in list(six.iterkeys(pkeys)):
        if table not in tables:
            del pkeys[table]
    for table in list(six.iterkeys(uniq)):
        if table not in tables:
            del uniq[table]


def upgrade():
    prune_tablenames()
    bind = op.get_bind()
    # Add new constraints with new names and remove old constrains with the
    # old, DB-specific names
    # foreign keys
    for local, remote in six.iteritems(fkeys):
        # Give None as the name to use the predefined naming scheme
        op.create_foreign_key(None, local[0], remote[0], [local[1]],
                [remote[1]])
    if bind.dialect.name == 'mysql':
        # foreign keys
        grouped_table_names = groupby(sorted(fkeys.keys()), lambda k: k[0])
        counted_table_names = [(i, len(list(j))) for i, j in
                grouped_table_names]
        for table_name, count in counted_table_names:
            for c in range(1, count+1):
                constraint_name = naming_schemes['mysql']['foreignkey'].format(
                        local_table=table_name,
                        table_num=c)
                op.drop_constraint(constraint_name, table_name,
                        type_='foreignkey')
    elif bind.dialect.name == 'postgresql':
        # foreign keys
        for table, column in fkeys.keys():
            constraint_name = naming_schemes['postgresql']['foreignkey'].\
                    format(local_table=table, local_col=column)
            op.drop_constraint(constraint_name, table)
    # primary keys
    # MySQL names all primary keys 'PRIMARY', and doesn't let you change them.
    if bind.dialect.name != 'mysql':
        for table, columns in pkeys:
            op.create_primary_key(None, table, columns)
            old_name = naming_schemes[bind.dialect.name]['primary'].format(
                    table_name=table)
            op.drop_constraint(old_name, table, type_='primary')
    # unique
    for table, columns in six.iteritems(uniq):
        op.create_unique_constraint(None, table, columns)
        if bind.dialect.name == 'postgresql':
            old_name = '{}_{}_key'.format(table, '_'.join(columns))
        else:
            old_name = naming_schemes[bind.dialect.name]['unique'].format(
                    table_name=table, columns=columns)
        op.drop_constraint(old_name, table, type_='unique')


def downgrade():
    prune_tablenames()
    # Add all the DB specific names back and remove the standard names
    bind = op.get_bind()
    # foreign keys
    counts = {}
    for local, remote in six.iteritems(fkeys):
        # add old
        current_count = counts.get(local[0], 1)
        old_name = naming_schemes[bind.dialect.name]['foreignkey'].format(
                local_table=local[0], local_col=local[1],
                remote_table=remote[0], remote_col=remote[1],
                table_num=current_count)
        op.create_foreign_key(old_name, local[0], remote[0],
                [local[1]], [remote[1]])
        # remove new
        new_name = naming_schemes['standard']['foreignkey'].format(
                local_table=local[0], local_col=local[1],
                remote_table=remote[0], remote_col=remote[1],
                table_num=current_count)
        op.drop_constraint(new_name, local[0], type_='foreignkey')
        counts[local[0]] = current_count + 1
    # primary keys
    if bind.dialect.name != 'mysql':
        for table, columns in pkeys:
            old_name = naming_schemes[bind.dialect.name]['primary'].format(
                    table_name=table)
            new_name = naming_schemes['standard']['primary'].format(
                    table_name=table)
            op.create_primary_key(old_name, table, columns)
            op.drop_constraint(new_name, table, type_='primary')

    # unique
    for table, columns in six.iteritems(uniq):
        if bind.dialect.name == 'postgresql':
            old_name = '{}_{}_key'.format(table, '_'.join(columns))
        else:
            old_name = naming_schemes[bind.dialect.name]['unique'].format(
                    table_name=table, columns=columns)
        op.create_unique_constraint(old_name, table, columns)
        new_name = naming_schemes['standard']['unique'].format(
                table_name=table, columns=columns)
        op.drop_constraint(new_name, table, type_='unique')
