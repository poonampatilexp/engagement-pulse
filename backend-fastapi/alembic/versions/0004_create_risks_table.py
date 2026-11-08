"""create risks table

Revision ID: 0004_create_risks_table
Revises: 0003_create_projects_table
Create Date: 2026-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_create_risks_table'
down_revision: Union[str, None] = '0003_create_projects_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'risks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('owner', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name='check_risk_severity_valid'),
        sa.CheckConstraint("status IN ('open', 'mitigating', 'closed')", name='check_risk_status_valid'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risks_id'), 'risks', ['id'], unique=False)
    op.create_index(op.f('ix_risks_project_id'), 'risks', ['project_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_risks_project_id'), table_name='risks')
    op.drop_index(op.f('ix_risks_id'), table_name='risks')
    op.drop_table('risks')

