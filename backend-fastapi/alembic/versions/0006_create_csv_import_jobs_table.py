"""create csv import jobs table

Revision ID: 0006_create_csv_import_jobs
Revises: 0005_create_scoring_weights
Create Date: 2026-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006_create_csv_import_jobs'
down_revision: Union[str, None] = '0005_create_scoring_weights'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'csv_import_jobs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'queued'"), nullable=False),
        sa.Column('total_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('processed_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('error_details', sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name='check_csv_job_status',
        ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_csv_import_jobs_created_by_id', 'csv_import_jobs', ['created_by_id'])
    op.create_index('ix_csv_import_jobs_project_id', 'csv_import_jobs', ['project_id'])
    op.create_index('ix_csv_import_jobs_status', 'csv_import_jobs', ['status'])
    op.create_index('ix_csv_import_jobs_file_hash', 'csv_import_jobs', ['file_hash'])


def downgrade() -> None:
    op.drop_index('ix_csv_import_jobs_file_hash', table_name='csv_import_jobs')
    op.drop_index('ix_csv_import_jobs_status', table_name='csv_import_jobs')
    op.drop_index('ix_csv_import_jobs_project_id', table_name='csv_import_jobs')
    op.drop_index('ix_csv_import_jobs_created_by_id', table_name='csv_import_jobs')
    op.drop_table('csv_import_jobs')

