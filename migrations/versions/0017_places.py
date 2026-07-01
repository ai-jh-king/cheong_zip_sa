"""places(생활·교육·운동 시설) 테이블 추가 — 공공데이터 + 향후 업체 등록 통합

Revision ID: 0017_places
Revises: 0016_search_trgm
Create Date: 2026-06-28

신규 테이블(additive)·멱등(inspect 가드). 학원·체육·도서관·병원 등을 한 모델로 normalize.
source(public/claimed/ad)로 공공/등록/광고 구분 — 향후 업체 직접 등록을 같은 테이블에 얹는다.
좌표 없으면 거리/지도 제외(왜곡 방지).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0017_places"
down_revision = "0016_search_trgm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if insp.has_table("places"):
        return
    op.create_table(
        "places",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=150), nullable=False, index=True),
        sa.Column("category", sa.String(length=24), nullable=False, index=True),
        sa.Column("subcategory", sa.String(length=32), nullable=False, index=True),
        sa.Column("course", sa.String(length=150), nullable=True),
        sa.Column("road_address", sa.String(length=200), nullable=True),
        sa.Column("lawd_cd", sa.String(length=5), nullable=True, index=True),
        sa.Column("dong_name", sa.String(length=40), nullable=True, index=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("tuition", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("attrs", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(length=12), nullable=False, server_default="public", index=True),
        sa.Column("source_dataset", sa.String(length=40), nullable=True),
        sa.Column("source_key", sa.String(length=160), nullable=False),
        sa.Column("claimed_by", sa.Integer(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("source_key", name="uq_places_source_key"),
    )
    op.create_index("ix_places_cat_lawd", "places", ["category", "lawd_cd"])
    op.create_index("ix_places_subcat_lawd", "places", ["subcategory", "lawd_cd"])


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("places"):
        return
    for ix in ("ix_places_cat_lawd", "ix_places_subcat_lawd"):
        try:
            op.drop_index(ix, table_name="places")
        except Exception:
            pass
    op.drop_table("places")
