"""monetization scaffolding(부록B): listings.is_sponsored/priority, accounts.plan 추가

Revision ID: 0012_monetization
Revises: 0011_jobrun
Create Date: 2026-06-25

추가형(additive)·멱등(inspect 가드). 전부 피처 플래그 뒤에서만 동작하며 기본 OFF이므로
이 컬럼들이 채워져도 현재 동작은 변하지 않는다(첫 출시에서 제외 가능).
- listings.is_sponsored : 광고/제휴 노출 여부(기본 0). feature_ads ON일 때만 목록 정렬에 반영.
- listings.priority     : 노출 우선순위(기본 0).
- accounts.plan         : free|premium(기본 free). feature_monetization ON일 때만 is_premium 반영.
타입은 portable(Boolean/Integer/String) — SQLite/PostgreSQL 공통. 기존 행은 server_default로 채움.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0012_monetization"
down_revision = "0011_jobrun"
branch_labels = None
depends_on = None

_LISTING_COLS = [
    ("is_sponsored", sa.Boolean(), sa.false()),
    ("priority", sa.Integer(), sa.text("0")),
]
_ACCOUNT_COLS = [
    ("plan", sa.String(length=20), sa.text("'free'")),
]


def _add(table, cols):
    insp = inspect(op.get_bind())
    if not insp.has_table(table):
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    for name, type_, default in cols:
        if name not in existing:
            op.add_column(table, sa.Column(name, type_, nullable=False, server_default=default))


def _drop(table, cols):
    insp = inspect(op.get_bind())
    if not insp.has_table(table):
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    for name, _t, _d in cols:
        if name in existing:
            op.drop_column(table, name)


def upgrade() -> None:
    _add("listings", _LISTING_COLS)
    _add("accounts", _ACCOUNT_COLS)


def downgrade() -> None:
    _drop("listings", _LISTING_COLS)
    _drop("accounts", _ACCOUNT_COLS)
