"""complexes: 공시가격 컬럼

Revision ID: 0006_gongsi
Revises: 0005_complex_meta
Create Date: 2026-06-19

추가형. 공동주택 공시가격(단지·면적 중앙값, 만원)과 공시기준일.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0006_gongsi"
down_revision = "0005_complex_meta"
branch_labels = None
depends_on = None

_COLS = [("price_official", sa.Integer()), ("price_basis_date", sa.String(length=20))]


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
