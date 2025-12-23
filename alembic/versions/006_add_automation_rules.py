"""Add automation rules

Revision ID: 006
Revises: 005
Create Date: 2024-01-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create automation_rules table
    op.create_table('automation_rules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('channel_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('rule_type', sa.String(length=50), nullable=True),
    sa.Column('trigger_field', sa.String(length=20), nullable=True),
    sa.Column('condition', sa.String(length=50), nullable=True),
    sa.Column('threshold_value', sa.Float(), nullable=True),
    sa.Column('target_field', sa.String(length=20), nullable=True),
    sa.Column('action_type', sa.String(length=50), nullable=True),
    sa.Column('action_value', sa.Float(), nullable=True),
    sa.Column('pid_setpoint', sa.Float(), nullable=True),
    sa.Column('pid_kp', sa.Float(), nullable=True),
    sa.Column('pid_ki', sa.Float(), nullable=True),
    sa.Column('pid_kd', sa.Float(), nullable=True),
    sa.Column('pid_integral', sa.Float(), nullable=True),
    sa.Column('pid_last_error', sa.Float(), nullable=True),
    sa.Column('pid_output_min', sa.Float(), nullable=True),
    sa.Column('pid_output_max', sa.Float(), nullable=True),
    sa.Column('expression', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('priority', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automation_rules_id'), 'automation_rules', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_automation_rules_id'), table_name='automation_rules')
    op.drop_table('automation_rules')



















