"""Add custom widgets

Revision ID: 005
Revises: 004
Create Date: 2024-01-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create custom_widgets table
    op.create_table('custom_widgets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('channel_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('widget_type', sa.String(length=50), nullable=True),
    sa.Column('svg_file_url', sa.String(length=500), nullable=True),
    sa.Column('svg_bindings', sa.Text(), nullable=True),
    sa.Column('html_code', sa.Text(), nullable=True),
    sa.Column('css_code', sa.Text(), nullable=True),
    sa.Column('js_code', sa.Text(), nullable=True),
    sa.Column('position', sa.Integer(), nullable=True),
    sa.Column('width', sa.Integer(), nullable=True),
    sa.Column('height', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_custom_widgets_id'), 'custom_widgets', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_custom_widgets_id'), table_name='custom_widgets')
    op.drop_table('custom_widgets')



















