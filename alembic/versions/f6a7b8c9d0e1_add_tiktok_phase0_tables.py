"""add tiktok phase0 tables

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-18 00:00:00.000000

Tạo 3 bảng cho TikTok Phase 0 Foundation:
  - hook_variants: lưu biến thể hook cho A/B test (Loop 4)
  - product_scores: theo dõi performance từng sản phẩm (Loop 5)
  - tag_queue_items: video chờ user tag sản phẩm lên TikTok
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from backend.compat import GUID

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- hook_variants ---
    op.create_table(
        "hook_variants",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("content_piece_id", GUID(), nullable=False),
        sa.Column("hook_text", sa.String(500), nullable=False),
        sa.Column("pattern_type", sa.String(30), nullable=False),
        sa.Column("retention_at_3s", sa.Float(), nullable=True),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["content_piece_id"],
            ["content_pieces.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_hook_variants_content_piece_id"),
        "hook_variants",
        ["content_piece_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_hook_variants_pattern_type"),
        "hook_variants",
        ["pattern_type"],
        unique=False,
    )

    # --- product_scores ---
    op.create_table(
        "product_scores",
        sa.Column("product_id", sa.String(100), nullable=False),
        sa.Column("actual_ctr", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("actual_conversion", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("return_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="active"
        ),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("product_id"),
    )
    op.create_index(
        op.f("ix_product_scores_status"),
        "product_scores",
        ["status"],
        unique=False,
    )

    # --- tag_queue_items ---
    op.create_table(
        "tag_queue_items",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("video_id", GUID(), nullable=False),
        sa.Column("tiktok_draft_url", sa.String(500), nullable=False),
        sa.Column("product_id", sa.String(100), nullable=False),
        sa.Column("product_name", sa.String(300), nullable=False),
        sa.Column("commission_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("tagged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["content_pieces.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tag_queue_items_video_id"),
        "tag_queue_items",
        ["video_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tag_queue_items_product_id"),
        "tag_queue_items",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tag_queue_items_product_id"), table_name="tag_queue_items")
    op.drop_index(op.f("ix_tag_queue_items_video_id"), table_name="tag_queue_items")
    op.drop_table("tag_queue_items")

    op.drop_index(op.f("ix_product_scores_status"), table_name="product_scores")
    op.drop_table("product_scores")

    op.drop_index(op.f("ix_hook_variants_pattern_type"), table_name="hook_variants")
    op.drop_index(op.f("ix_hook_variants_content_piece_id"), table_name="hook_variants")
    op.drop_table("hook_variants")
