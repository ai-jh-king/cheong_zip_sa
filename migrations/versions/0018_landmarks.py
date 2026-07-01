"""landmarks(개발 호재) 테이블 — 청주 하이퍼로컬 호재 지도

Revision ID: 0018_landmarks
Revises: 0017_places
Create Date: 2026-06-28

신규 테이블(additive)·멱등. 위치+사실+출처. status(확정/추진/계획)·출처로 왜곡 방지.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0018_landmarks"
down_revision = "0017_places"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if insp.has_table("landmarks"):
        return
    op.create_table(
        "landmarks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False, index=True),
        sa.Column("status", sa.String(length=12), nullable=False, index=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("summary", sa.String(length=400), nullable=True),
        sa.Column("expected_year", sa.Integer(), nullable=True),
        sa.Column("source_name", sa.String(length=120), nullable=True),
        sa.Column("source_url", sa.String(length=400), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true(), index=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if insp.has_table("landmarks"):
        op.drop_table("landmarks")
