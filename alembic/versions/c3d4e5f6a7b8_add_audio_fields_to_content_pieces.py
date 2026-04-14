"""add_audio_fields_to_content_pieces

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-14 10:00:00.000000

Thêm 3 cột ElevenLabs audio vào bảng content_pieces:
  - audio_url: URL file MP3 (lưu tại /static/audio/)
  - audio_voice_id: Voice ID ElevenLabs đã dùng để tổng hợp
  - audio_duration_s: Thời lượng ước tính (giây)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'content_pieces',
        sa.Column('audio_url', sa.String(length=500), nullable=True),
    )
    op.add_column(
        'content_pieces',
        sa.Column('audio_voice_id', sa.String(length=100), nullable=True),
    )
    op.add_column(
        'content_pieces',
        sa.Column('audio_duration_s', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('content_pieces', 'audio_duration_s')
    op.drop_column('content_pieces', 'audio_voice_id')
    op.drop_column('content_pieces', 'audio_url')
