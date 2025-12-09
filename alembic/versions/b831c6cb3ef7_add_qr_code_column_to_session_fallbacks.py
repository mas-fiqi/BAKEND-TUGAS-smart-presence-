"""add qr_code column to session_fallbacks

Revision ID: b831c6cb3ef7
Revises: 42d2cd1a061c
Create Date: 2025-12-07 16:43:13.156906

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b831c6cb3ef7'
down_revision: Union[str, Sequence[str], None] = '42d2cd1a061c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add qr_code column to session_fallbacks table
    op.add_column('session_fallbacks', sa.Column('qr_code', sa.String(length=128), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove qr_code column from session_fallbacks table
    op.drop_column('session_fallbacks', 'qr_code')
