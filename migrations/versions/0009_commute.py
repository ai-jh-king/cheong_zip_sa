"""commute: 통근권 목적지/사전계산 캐시 테이블

Revision ID: 0009_commute
Revises: 0008_tx_trade_method
Create Date: 2026-06-21

추가형(additive). 통근권 검색용 두 테이블.
- commute_destinations: 운영자 관리 목적지(직장·교통·공공 등).
- commute_times: (단지×목적지×수단) 통근시간 캐시. 'N분 이내' 조회 인덱스 포함.
inspect 가드로 멱등(fresh DB는 0002 create_all 로 이미 생성됨). 타입 portable.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0009_commute"
down_revision = "0008_tx_trade_method"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("commute_destinations"):
        op.create_table(
            "commute_destinations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("key", sa.String(length=40), nullable=False),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("category", sa.String(length=20), nullable=False),
            sa.Column("lat", sa.Float(), nullable=True),
            sa.Column("lng", sa.Float(), nullable=True),
            sa.Column("address", sa.String(length=200), nullable=True),
            sa.Column("gu", sa.String(length=20), nullable=True),
            sa.Column("coord_method", sa.String(length=20), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("key", name="uq_commute_dest_key"),
        )
        op.create_index("ix_commute_destinations_is_active", "commute_destinations", ["is_active"])

    if not insp.has_table("commute_times"):
        op.create_table(
            "commute_times",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("complex_id", sa.Integer(), sa.ForeignKey("complexes.id"), nullable=False),
            sa.Column("destination_id", sa.Integer(), sa.ForeignKey("commute_destinations.id"), nullable=False),
            sa.Column("mode", sa.String(length=10), nullable=False),
            sa.Column("minutes", sa.Integer(), nullable=True),
            sa.Column("distance_m", sa.Integer(), nullable=True),
            sa.Column("method", sa.String(length=12), nullable=False),
            sa.Column("source", sa.String(length=40), nullable=True),
            sa.Column("computed_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("complex_id", "destination_id", "mode", name="uq_commute"),
        )
        op.create_index("ix_commute_times_complex_id", "commute_times", ["complex_id"])
        op.create_index("ix_commute_times_destination_id", "commute_times", ["destination_id"])
        op.create_index("ix_commute_dest_mode_min", "commute_times", ["destination_id", "mode", "minutes"])


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if insp.has_table("commute_times"):
        op.drop_table("commute_times")
    if insp.has_table("commute_destinations"):
        op.drop_table("commute_destinations")
