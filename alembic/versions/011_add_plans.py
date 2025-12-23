"""Add plans and plan_items tables

Revision ID: 011
Revises: 010
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Проверяем существование таблиц перед созданием (для случаев, когда таблицы уже созданы вручную)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create plans table (если не существует)
    if 'plans' not in existing_tables:
        op.create_table(
            'plans',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('channel_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_default', sa.Boolean(), nullable=True),
            sa.Column('layout_config', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_plans_id'), 'plans', ['id'], unique=False)
        op.create_index(op.f('ix_plans_channel_id'), 'plans', ['channel_id'], unique=False)
    else:
        # Таблица уже существует, проверяем индексы
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('plans')]
        if 'ix_plans_id' not in existing_indexes:
            op.create_index(op.f('ix_plans_id'), 'plans', ['id'], unique=False)
        if 'ix_plans_channel_id' not in existing_indexes:
            op.create_index(op.f('ix_plans_channel_id'), 'plans', ['channel_id'], unique=False)
    
    # Create plan_items table (если не существует)
    if 'plan_items' not in existing_tables:
        op.create_table(
            'plan_items',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('plan_id', sa.Integer(), nullable=False),
            sa.Column('item_type', sa.String(length=50), nullable=False),
            sa.Column('source_widget_id', sa.Integer(), nullable=True),
            sa.Column('source_channel_id', sa.Integer(), nullable=True),
            sa.Column('position_x', sa.Float(), nullable=True),
            sa.Column('position_y', sa.Float(), nullable=True),
            sa.Column('width', sa.Integer(), nullable=True),
            sa.Column('height', sa.Integer(), nullable=True),
            sa.Column('z_index', sa.Integer(), nullable=True),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('file_url', sa.String(length=500), nullable=True),
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_widget_id'], ['custom_widgets.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['source_channel_id'], ['channels.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_plan_items_id'), 'plan_items', ['id'], unique=False)
        op.create_index(op.f('ix_plan_items_plan_id'), 'plan_items', ['plan_id'], unique=False)
    else:
        # Таблица уже существует, проверяем индексы
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('plan_items')]
        if 'ix_plan_items_id' not in existing_indexes:
            op.create_index(op.f('ix_plan_items_id'), 'plan_items', ['id'], unique=False)
        if 'ix_plan_items_plan_id' not in existing_indexes:
            op.create_index(op.f('ix_plan_items_plan_id'), 'plan_items', ['plan_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_plan_items_plan_id'), table_name='plan_items')
    op.drop_index(op.f('ix_plan_items_id'), table_name='plan_items')
    op.drop_table('plan_items')
    op.drop_index(op.f('ix_plans_channel_id'), table_name='plans')
    op.drop_index(op.f('ix_plans_id'), table_name='plans')
    op.drop_table('plans')

