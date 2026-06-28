"""transactions: 거래유형(중개/직거래) 컬럼 추가 — 실거래 신뢰 필터용

Revision ID: 0008_tx_trade_method
Revises: 0007_search_index
Create Date: 2026-06-21

추가형(additive)·nullable. 국토부 매매 응답의 '거래유형'(중개거래/직거래)을 보관해
직거래(가족 간 증여성 등) 거래를 시세 해석 시 구분/표시하기 위함.
값 규약: 'agent'(중개) / 'direct'(직거래) / NULL(미상·전월세 등 미제공).
inspect 가드로 멱등. 타입은 portable(String) — SQLite/PostgreSQL 공통.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0008_tx_trade_method"
down_revision = "0007_search_index"
branch_labels = None
depends_on = None

_COLS = [
    ("trade_method", sa.String(length=12)),
]


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("transactions"):
        return
    existing = {c["name"] for c in insp.get_columns("transactions")}
    for name, type_ in _COLS:
        if name not in existing:
            op.add_column("transactions", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("transactions"):
        return
    existing = {c["name"] for c in insp.get_columns("transactions")}
    for name, _ in _COLS:
        if name in existing:
            op.drop_column("transactions", name)
