"""Archive settings table

Revision ID: 009
Revises: 008
Create Date: 2025-11-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    archive_backend_enum = sa.Enum('sqlite', 'postgres', name='archivebackendtype')
    archive_backend_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'archive_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('backend_type', archive_backend_enum, nullable=False, server_default='sqlite'),
        sa.Column('sqlite_file_path', sa.String(length=500), nullable=True),
        sa.Column('pg_host', sa.String(length=255), nullable=True),
        sa.Column('pg_port', sa.Integer(), nullable=True),
        sa.Column('pg_db', sa.String(length=255), nullable=True),
        sa.Column('pg_user', sa.String(length=255), nullable=True),
        sa.Column('pg_password_enc', sa.Text(), nullable=True),
        sa.Column('pg_schema', sa.String(length=255), nullable=True),
        sa.Column('pg_ssl', sa.Boolean(), nullable=True),
        sa.Column('retention_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('schedule_interval_seconds', sa.Integer(), nullable=False, server_default='3600'),
        sa.Column('schedule_cron', sa.String(length=100), nullable=True),
        sa.Column('copy_then_delete', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_status', sa.String(length=50), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_processed', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_archive_settings_id'), 'archive_settings', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_archive_settings_id'), table_name='archive_settings')
    op.drop_table('archive_settings')

    archive_backend_enum = sa.Enum('sqlite', 'postgres', name='archivebackendtype')
    archive_backend_enum.drop(op.get_bind(), checkfirst=True)

