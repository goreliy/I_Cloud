"""Add request logging

Revision ID: 004
Revises: 003
Create Date: 2024-01-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create request_logs table
    op.create_table('request_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('channel_id', sa.Integer(), nullable=True),
    sa.Column('endpoint', sa.String(length=500), nullable=False),
    sa.Column('method', sa.String(length=10), nullable=False),
    sa.Column('ip_address', sa.String(length=50), nullable=True),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.Column('response_status', sa.Integer(), nullable=False),
    sa.Column('response_time', sa.Float(), nullable=False),
    sa.Column('api_key_used', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_request_logs_id'), 'request_logs', ['id'], unique=False)
    op.create_index(op.f('ix_request_logs_timestamp'), 'request_logs', ['timestamp'], unique=False)
    op.create_index('ix_request_logs_timestamp_status', 'request_logs', ['timestamp', 'response_status'], unique=False)
    op.create_index('ix_request_logs_user_timestamp', 'request_logs', ['user_id', 'timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_request_logs_user_timestamp', table_name='request_logs')
    op.drop_index('ix_request_logs_timestamp_status', table_name='request_logs')
    op.drop_index(op.f('ix_request_logs_timestamp'), table_name='request_logs')
    op.drop_index(op.f('ix_request_logs_id'), table_name='request_logs')
    op.drop_table('request_logs')



















