"""Add field visibility columns to channels table

Revision ID: 012
Revises: 011
Create Date: 2025-01-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Проверяем существование колонок перед добавлением
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Получаем список существующих колонок в таблице channels
    if 'channels' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('channels')]
        
        # Добавляем колонки видимости полей, если их еще нет
        for i in range(1, 9):
            col_name = f'field{i}_visible'
            if col_name not in existing_columns:
                op.add_column('channels', sa.Column(col_name, sa.Boolean(), server_default=sa.true(), nullable=False))
        
        # Обновляем существующие записи, устанавливая все поля видимыми (на случай, если server_default не сработал)
        op.execute("UPDATE channels SET field1_visible = 1, field2_visible = 1, field3_visible = 1, field4_visible = 1, field5_visible = 1, field6_visible = 1, field7_visible = 1, field8_visible = 1 WHERE field1_visible IS NULL")


def downgrade() -> None:
    # Удаляем колонки видимости полей
    for i in range(1, 9):
        try:
            op.drop_column('channels', f'field{i}_visible')
        except Exception:
            pass  # Игнорируем ошибки, если колонка не существует

