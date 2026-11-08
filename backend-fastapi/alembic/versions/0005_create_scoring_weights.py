"""create scoring weights

Revision ID: 0005_create_scoring_weights
Revises: 0004_create_risks_table
Create Date: 2026-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005_create_scoring_weights'
down_revision: Union[str, None] = '0004_create_risks_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'severity_weights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=False),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name='check_severity_weight_valid'),
        sa.CheckConstraint('weight > 0', name='check_severity_weight_positive'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('severity', name='uq_severity_weights_severity')
    )
    op.create_index(op.f('ix_severity_weights_id'), 'severity_weights', ['id'], unique=False)

    op.create_table(
        'status_weights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=False),
        sa.CheckConstraint("status IN ('open', 'mitigating', 'closed')", name='check_status_weight_valid'),
        sa.CheckConstraint('weight >= 0', name='check_status_weight_nonnegative'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('status', name='uq_status_weights_status')
    )
    op.create_index(op.f('ix_status_weights_id'), 'status_weights', ['id'], unique=False)

    # Seed initial values using explicit SQL inserts
    op.execute(
        sa.text(
            """
            INSERT INTO severity_weights (severity, weight) VALUES
                ('low', 1),
                ('medium', 2),
                ('high', 3),
                ('critical', 4)
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO status_weights (status, weight) VALUES
                ('open', 3),
                ('mitigating', 2),
                ('closed', 0)
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_status_weights_id'), table_name='status_weights')
    op.drop_table('status_weights')
    op.drop_index(op.f('ix_severity_weights_id'), table_name='severity_weights')
    op.drop_table('severity_weights')

