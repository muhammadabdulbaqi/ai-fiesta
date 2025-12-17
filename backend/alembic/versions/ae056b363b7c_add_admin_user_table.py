"""add_admin_user_table

Revision ID: ae056b363b7c
Revises: 47483be28476
Create Date: 2025-12-17 07:45:07.376622

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae056b363b7c'
down_revision: Union[str, None] = '47483be28476'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if 'admin_users' not in tables:
        op.create_table('admin_users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_admin_users_email'), 'admin_users', ['email'], unique=True)
        op.create_index(op.f('ix_admin_users_username'), 'admin_users', ['username'], unique=True)
    else:
        # Table exists, but check if indexes exist
        indexes = [idx['name'] for idx in inspector.get_indexes('admin_users')]
        if 'ix_admin_users_email' not in indexes:
            op.create_index(op.f('ix_admin_users_email'), 'admin_users', ['email'], unique=True)
        if 'ix_admin_users_username' not in indexes:
            op.create_index(op.f('ix_admin_users_username'), 'admin_users', ['username'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_admin_users_username'), table_name='admin_users')
    op.drop_index(op.f('ix_admin_users_email'), table_name='admin_users')
    op.drop_table('admin_users')
