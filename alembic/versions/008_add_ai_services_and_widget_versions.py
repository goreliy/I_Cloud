"""Add AI services configuration and widget versions history

Revision ID: 008
Revises: 007
Create Date: 2025-11-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    ai_scope_enum = sa.Enum('global', 'channel', 'widget', name='ai_scope_enum')
    ai_scope_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'ai_services',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('alias', sa.String(length=100), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column('display_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('default_prompt_common', sa.Text(), nullable=True),
        sa.Column('default_prompt_html', sa.Text(), nullable=True),
        sa.Column('default_prompt_css', sa.Text(), nullable=True),
        sa.Column('default_prompt_js', sa.Text(), nullable=True),
        sa.Column('default_prompt_refine', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('alias'),
    )
    op.create_index(op.f('ix_ai_services_id'), 'ai_services', ['id'], unique=False)

    op.create_table(
        'ai_service_prompts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.Column('scope', ai_scope_enum, nullable=False, server_default='global'),
        sa.Column('channel_id', sa.Integer(), nullable=True),
        sa.Column('widget_id', sa.Integer(), nullable=True),
        sa.Column('prompt_common', sa.Text(), nullable=True),
        sa.Column('prompt_html', sa.Text(), nullable=True),
        sa.Column('prompt_css', sa.Text(), nullable=True),
        sa.Column('prompt_js', sa.Text(), nullable=True),
        sa.Column('prompt_refine', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['service_id'], ['ai_services.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['widget_id'], ['custom_widgets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_service_prompts_id'), 'ai_service_prompts', ['id'], unique=False)
    op.create_index('ix_ai_service_prompts_channel_id', 'ai_service_prompts', ['channel_id'], unique=False)
    op.create_index('ix_ai_service_prompts_widget_id', 'ai_service_prompts', ['widget_id'], unique=False)

    op.create_table(
        'widget_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('widget_id', sa.Integer(), nullable=False),
        sa.Column('ai_service_id', sa.Integer(), nullable=True),
        sa.Column('prompt_used', sa.Text(), nullable=True),
        sa.Column('comment', sa.String(length=255), nullable=True),
        sa.Column('html_code', sa.Text(), nullable=True),
        sa.Column('css_code', sa.Text(), nullable=True),
        sa.Column('js_code', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['ai_service_id'], ['ai_services.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['widget_id'], ['custom_widgets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_widget_versions_id'), 'widget_versions', ['id'], unique=False)
    op.create_index('ix_widget_versions_widget_id', 'widget_versions', ['widget_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_widget_versions_widget_id', table_name='widget_versions')
    op.drop_index(op.f('ix_widget_versions_id'), table_name='widget_versions')
    op.drop_table('widget_versions')

    op.drop_index('ix_ai_service_prompts_widget_id', table_name='ai_service_prompts')
    op.drop_index('ix_ai_service_prompts_channel_id', table_name='ai_service_prompts')
    op.drop_index(op.f('ix_ai_service_prompts_id'), table_name='ai_service_prompts')
    op.drop_table('ai_service_prompts')

    op.drop_index(op.f('ix_ai_services_id'), table_name='ai_services')
    op.drop_table('ai_services')

    ai_scope_enum = sa.Enum('global', 'channel', 'widget', name='ai_scope_enum')
    ai_scope_enum.drop(op.get_bind(), checkfirst=True)

