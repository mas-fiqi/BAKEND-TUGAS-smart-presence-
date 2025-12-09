"""add status column to attendance_sessions

Revision ID: 42d2cd1a061c
Revises: 
Create Date: 2025-12-07 16:15:54.993153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '42d2cd1a061c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add status column to attendance_sessions table
    op.add_column('attendance_sessions', sa.Column('status', sa.String(), nullable=False, server_default='draft'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove status column from attendance_sessions table
    op.drop_column('attendance_sessions', 'status')
