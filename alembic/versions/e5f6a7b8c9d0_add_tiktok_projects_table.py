"""add_tiktok_projects_table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-16 10:00:00.000000

Tạo bảng tiktok_projects để theo dõi vòng đời sản xuất video TikTok:
  script_pending → script_ready → audio_ready → clips_ready
  → b_roll_pending → editing → uploaded → live
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tiktok_projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id'), nullable=True),
        sa.Column('product_name', sa.String(200), nullable=False),
        sa.Column('product_ref_url', sa.String(500), nullable=True),
        sa.Column('content_id', sa.String(36), sa.ForeignKey('content_pieces.id'), nullable=True),
        sa.Column('script_body', sa.Text(), nullable=True),
        sa.Column('angle', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('audio_url', sa.String(500), nullable=True),
        sa.Column('audio_voice_id', sa.String(100), nullable=True),
        sa.Column('audio_duration_s', sa.Float(), nullable=True),
        sa.Column('heygen_hook_url', sa.String(1000), nullable=True),
        sa.Column('heygen_cta_url', sa.String(1000), nullable=True),
        sa.Column('script_ready_at', sa.DateTime(), nullable=True),
        sa.Column('audio_ready_at', sa.DateTime(), nullable=True),
        sa.Column('clips_ready_at', sa.DateTime(), nullable=True),
        sa.Column('b_roll_filmed_at', sa.DateTime(), nullable=True),
        sa.Column('editing_done_at', sa.DateTime(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='script_pending'),
        sa.Column('tiktok_video_id', sa.String(200), nullable=True),
        sa.Column('tiktok_video_url', sa.String(500), nullable=True),
        sa.Column('views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('likes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('shares', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_tiktok_projects_status', 'tiktok_projects', ['status'])
    op.create_index('ix_tiktok_projects_created_at', 'tiktok_projects', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_tiktok_projects_created_at', table_name='tiktok_projects')
    op.drop_index('ix_tiktok_projects_status', table_name='tiktok_projects')
    op.drop_table('tiktok_projects')
