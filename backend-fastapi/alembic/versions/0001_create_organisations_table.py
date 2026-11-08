"""create organisations table

Revision ID: 0001_create_organisations
Revises: 
Create Date: 2026-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_create_organisations'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'organisations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_organisations_id'), 'organisations', ['id'], unique=False)
    op.create_index(op.f('ix_organisations_slug'), 'organisations', ['slug'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_organisations_slug'), table_name='organisations')
    op.drop_index(op.f('ix_organisations_id'), table_name='organisations')
    op.drop_table('organisations')

