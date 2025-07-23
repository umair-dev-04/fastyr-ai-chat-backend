"""Rename username column to full_name

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename username column to full_name
    op.alter_column('users', 'username', new_column_name='full_name')
    
    # Rename the index as well
    op.drop_index('ix_users_username', table_name='users')
    op.create_index('ix_users_full_name', 'users', ['full_name'], unique=True)


def downgrade() -> None:
    # Rename full_name column back to username
    op.alter_column('users', 'full_name', new_column_name='username')
    
    # Rename the index back
    op.drop_index('ix_users_full_name', table_name='users')
    op.create_index('ix_users_username', 'users', ['username'], unique=True) 