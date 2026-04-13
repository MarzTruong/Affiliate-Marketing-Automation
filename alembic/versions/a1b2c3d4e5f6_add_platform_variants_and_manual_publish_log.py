"""add_platform_variants_and_manual_publish_log

Revision ID: a1b2c3d4e5f6
Revises: ffc02157caee
Create Date: 2026-04-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from backend.compat import GUID, JSONType


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'ffc02157caee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Thêm cột platform_variants vào content_pieces
    op.add_column(
        'content_pieces',
        sa.Column('platform_variants', JSONType(), nullable=True),
    )

    # Tạo bảng manual_publish_log
    op.create_table(
        'manual_publish_log',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('content_id', GUID(), nullable=False),
        sa.Column('platform', sa.String(length=30), nullable=False),
        sa.Column(
            'published_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['content_id'], ['content_pieces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_manual_publish_log_content_id'),
        'manual_publish_log',
        ['content_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_manual_publish_log_content_id'), table_name='manual_publish_log')
    op.drop_table('manual_publish_log')
    op.drop_column('content_pieces', 'platform_variants')
