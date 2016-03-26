"""Generalize attribute transformers for divisions.

Revision ID: 4280bf2417c
Revises: 2976d59f286
Create Date: 2014-06-18 22:01:20.924226

"""

# revision identifiers, used by Alembic.
revision = '4280bf2417c'
down_revision = '2976d59f286'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import update, select, table, column, or_
import evesrp.transformers


division = table('division',
        column('id', sa.Integer),
        column('ship_transformer', sa.PickleType),
        column('pilot_transformer', sa.PickleType),
)

transformerref = table('transformerref',
        column('division_id', sa.Integer),
        column('attribute_name', sa.String(length=50)),
        column('transformer', sa.PickleType),
)


# This is tricky: Ensure that evesrp.transformers has ShipTransformer and
# PilotTransformer classes so pickle con unpack them
for legacy_transformer in ('ShipTransformer', 'PilotTransformer'):
    if not hasattr(evesrp.transformers, legacy_transformer):
        new_class = type(legacy_transformer,
                (evesrp.transformers.Transformer,), {})
        setattr(evesrp.transformers, legacy_transformer, new_class)


def upgrade():
    # Create new transformerref table
    op.create_table('transformerref',
            sa.Column('id', sa.Integer, nullable=False, primary_key=True),
            sa.Column('attribute_name', sa.String(length=50), nullable=False),
            sa.Column('transformer', sa.PickleType, nullable=False),
            sa.Column('division_id', sa.Integer, nullable=False),
            sa.ForeignKeyConstraint(['division_id'], ['division.id'], ),
            sa.UniqueConstraint('division_id', 'attribute_name')
    )
    # Migrate ship and pilot transformers
    conn = op.get_bind()
    columns = [division.c.id, division.c.ship_transformer,
        division.c.pilot_transformer]
    transformer_sel = select(columns)\
            .where(or_(
                    division.c.ship_transformer != None,
                    division.c.pilot_transformer != None
            ))
    transformer_rows = conn.execute(transformer_sel)
    new_transformers = []
    for division_id, ship_transformer, pilot_transformer in transformer_rows:
        if ship_transformer is not None:
            transformer = evesrp.transformers.Transformer(
                    ship_transformer.name,
                    ship_transformer.slug)
            new_transformers.append({
                    'attribute_name': 'ship_type',
                    'transformer': transformer,
                    'division_id': division_id,
            })
        if pilot_transformer is not None:
            transformer = evesrp.transformers.Transformer(
                    pilot_transformer.name,
                    pilot_transformer.slug)
            new_transformers.append({
                    'attribute_name': 'pilot',
                    'transformer': transformer,
                    'division_id': division_id,
            })
    transformer_rows.close()
    op.bulk_insert(transformerref, new_transformers)
    # Drop old columns
    op.drop_column('division', 'ship_transformer')
    op.drop_column('division', 'pilot_transformer')


def downgrade():
    # Add ship and pilot transformer columns back to division
    op.add_column('division', sa.Column('ship_transformer', sa.PickleType))
    op.add_column('division', sa.Column('pilot_transformer', sa.PickleType))
    # Convert transformerrefs back to the old columns
    conn = op.get_bind()
    columns = [
        transformerref.c.division_id,
        transformerref.c.attribute_name,
        transformerref.c.transformer,
    ]
    transformer_sel = select(columns)\
            .where(or_(
                    transformerref.c.attribute_name == 'ship_type',
                    transformerref.c.attribute_name == 'pilot',
            ))
    transformer_rows = conn.execute(transformer_sel)
    for division_id, attribute_name, transformer in transformer_rows:
        if attribute_name == 'ship_type':
            colname = 'ship'
            transformer_class = evesrp.transformers.ShipTransformer
        elif attribute_name == 'pilot':
            colname = 'pilot'
            transformer_class = evesrp.transformers.PilotTransformer
        colname += '_transformer'
        transformer = transformer_class(transformer.name, transformer.slug)
        update_stmt = update(division)\
                .where(division.c.id == division_id)\
                .values({
                        colname: transformer
                })
        conn.execute(update_stmt)
    transformer_rows.close()
    # Drop the transformerref table. This is going to be lossy.
    op.drop_table('transformerref')
