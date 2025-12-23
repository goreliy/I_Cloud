"""Add stress test runs table

Revision ID: 007
Revises: 006
Create Date: 2025-10-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'stress_test_runs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('workers', sa.Integer(), nullable=False),
        sa.Column('target_rps', sa.Integer(), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=True),
        sa.Column('successful_requests', sa.Integer(), nullable=True),
        sa.Column('failed_requests', sa.Integer(), nullable=True),
        sa.Column('actual_rps', sa.Float(), nullable=True),
        sa.Column('avg_latency_ms', sa.Float(), nullable=True),
        sa.Column('min_latency_ms', sa.Float(), nullable=True),
        sa.Column('max_latency_ms', sa.Float(), nullable=True),
        sa.Column('p95_latency_ms', sa.Float(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('results_json', sa.Text(), nullable=True),
    )
    
    op.create_index('ix_stress_test_runs_channel_id', 'stress_test_runs', ['channel_id'])
    op.create_index('ix_stress_test_runs_status', 'stress_test_runs', ['status'])
    op.create_index('ix_stress_test_runs_started_at', 'stress_test_runs', ['started_at'])


def downgrade():
    op.drop_index('ix_stress_test_runs_started_at', 'stress_test_runs')
    op.drop_index('ix_stress_test_runs_status', 'stress_test_runs')
    op.drop_index('ix_stress_test_runs_channel_id', 'stress_test_runs')
    op.drop_table('stress_test_runs')


















