"""add_heygen_fields_to_content_pieces

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-14 11:00:00.000000

Thêm 2 cột HeyGen video clips vào bảng content_pieces:
  - heygen_hook_url: URL clip avatar hook (0–3s)
  - heygen_cta_url: URL clip avatar CTA (36–45s)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'content_pieces',
        sa.Column('heygen_hook_url', sa.String(length=1000), nullable=True),
    )
    op.add_column(
        'content_pieces',
        sa.Column('heygen_cta_url', sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('content_pieces', 'heygen_cta_url')
    op.drop_column('content_pieces', 'heygen_hook_url')
