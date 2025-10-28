"""add token_version to users

Revision ID: 082893c49a86
Revises: 215287243eef
Create Date: 2025-10-26 23:02:02.720520
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '082893c49a86'
down_revision: Union[str, Sequence[str], None] = '215287243eef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1️⃣: 新增欄位但允許 NULL（避免舊資料報錯）
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=True))

    # Step 2️⃣: 將既有資料設為 0
    op.execute("UPDATE users SET token_version = 0")

    # Step 3️⃣: 鎖回 NOT NULL
    op.alter_column('users', 'token_version', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'token_version')
