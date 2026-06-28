"""complexes: 단지 기본정보 보강 컬럼(K-apt)

Revision ID: 0005_complex_meta
Revises: 0004_consents
Create Date: 2026-06-19

추가형(additive). 공동주택 기본정보(세대수·동수·사용승인일·난방·연면적·시공사·주차 등).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0005_complex_meta"
down_revision = "0004_consents"
branch_labels = None
depends_on = None

_COLS = [
    ("kapt_code", sa.String(length=20)),
    ("dong_count", sa.Integer()),
    ("heating", sa.String(length=40)),
    ("total_area", sa.Float()),
    ("builder", sa.String(length=120)),
    ("approval_date", sa.String(length=20)),
    ("parking", sa.Integer()),
    ("meta_source", sa.String(length=40)),
    ("enriched_at", sa.DateTime()),
]


def upgrade() -> None:
    insp = inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("complexes")} if insp.has_table("complexes") else set()
    for name, type_ in _COLS:
        if name not in existing:
            op.add_column("complexes", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    insp = inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("complexes")} if insp.has_table("complexes") else set()
    for name, _ in _COLS:
        if name in existing:
            op.drop_column("complexes", name)
