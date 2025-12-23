"""Add channel customization

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add customization columns to channels
    op.add_column('channels', sa.Column('image_url', sa.String(length=500), nullable=True))
    op.add_column('channels', sa.Column('background_url', sa.String(length=500), nullable=True))
    op.add_column('channels', sa.Column('color_scheme', sa.String(length=50), nullable=True, server_default='light'))
    op.add_column('channels', sa.Column('custom_css', sa.Text(), nullable=True))
    
    # Add field labels
    op.add_column('channels', sa.Column('field1_label', sa.String(length=100), nullable=True))
    op.add_column('channels', sa.Column('field2_label', sa.String(length=100), nullable=True))
    op.add_column('channels', sa.Column('field3_label', sa.String(length=100), nullable=True))
    op.add_column('channels', sa.Column('field4_label', sa.String(length=100), nullable=True))
    op.add_column('channels', sa.Column('field5_label', sa.String(length=100), nullable=True))
    op.add_column('channels', sa.Column('field6_label', sa.String(length=100), nullable=True))
    op.add_column('channels', sa.Column('field7_label', sa.String(length=100), nullable=True))
    op.add_column('channels', sa.Column('field8_label', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove customization columns
    op.drop_column('channels', 'field8_label')
    op.drop_column('channels', 'field7_label')
    op.drop_column('channels', 'field6_label')
    op.drop_column('channels', 'field5_label')
    op.drop_column('channels', 'field4_label')
    op.drop_column('channels', 'field3_label')
    op.drop_column('channels', 'field2_label')
    op.drop_column('channels', 'field1_label')
    op.drop_column('channels', 'custom_css')
    op.drop_column('channels', 'color_scheme')
    op.drop_column('channels', 'background_url')
    op.drop_column('channels', 'image_url')



















