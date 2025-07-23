"""Add OAuth fields to users table

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add OAuth fields to users table
    op.add_column('users', sa.Column('google_id', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('auth_provider', sa.String(length=50), nullable=True, server_default='email'))
    
    # Make hashed_password nullable for OAuth users
    op.alter_column('users', 'hashed_password', nullable=True)
    
    # Create indexes for OAuth fields
    op.create_index('ix_users_google_id', 'users', ['google_id'], unique=True)


def downgrade() -> None:
    # Drop OAuth indexes
    op.drop_index('ix_users_google_id', table_name='users')
    
    # Drop OAuth columns
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'google_id')
    
    # Make hashed_password not nullable again
    op.alter_column('users', 'hashed_password', nullable=False) 