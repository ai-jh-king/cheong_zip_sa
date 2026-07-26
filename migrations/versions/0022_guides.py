"""집사 도감 — guide_series(시리즈) + guides(편, 마크다운 본문).

콘텐츠 시스템: 더보기 → 집사 도감. 관리자 큐레이션(주 1편), 왜곡 없음(사실+근거만).
첫 시리즈('cheongju')는 scripts.seed_guides 로 시드(마이그레이션은 스키마만)."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0022_guides"
down_revision = "0021_perf_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("guide_series"):
        op.create_table(
            "guide_series",
            sa.Column("key", sa.String(length=40), primary_key=True, nullable=False),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("description", sa.String(length=300), nullable=True),
            sa.Column("cover_emoji", sa.String(length=8), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.create_index("ix_guide_series_is_active", "guide_series", ["is_active"])
    if not insp.has_table("guides"):
        op.create_table(
            "guides",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("series_key", sa.String(length=40), nullable=False),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("body_md", sa.Text(), nullable=False),
            sa.Column("cover_emoji", sa.String(length=8), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("published_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_guides_series_key", "guides", ["series_key"])
        op.create_index("ix_guides_series_pub", "guides", ["series_key", "is_published"])


def downgrade() -> None:
    op.drop_table("guides")
    op.drop_table("guide_series")
