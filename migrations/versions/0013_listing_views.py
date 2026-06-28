"""listings.views(조회수) 컬럼 추가 — 중개사 대시보드 v2

Revision ID: 0013_listing_views
Revises: 0012_monetization
Create Date: 2026-06-25

추가형(additive)·멱등(inspect 가드)·server_default 0. 외부 상세조회 시에만 증가(소유자 제외).
타입 portable(Integer). 기존 행은 0으로 채움.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0013_listing_views"
down_revision = "0012_monetization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("listings"):
        return
    existing = {c["name"] for c in insp.get_columns("listings")}
    if "views" not in existing:
        op.add_column("listings", sa.Column("views", sa.Integer(), nullable=False, server_default=sa.text("0")))


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("listings"):
        return
    existing = {c["name"] for c in insp.get_columns("listings")}
    if "views" in existing:
        op.drop_column("listings", "views")
