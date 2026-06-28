"""consents: 동의 이력(개인정보 9.A)

Revision ID: 0004_consents
Revises: 0003_tx_alerts
Create Date: 2026-06-19

대출 민감정보 등 개인정보 처리 동의의 버전·시각 기록. 추가형(additive).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0004_consents"
down_revision = "0003_tx_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("consents"):
        op.create_table(
            "consents",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("owner", sa.String(length=80), nullable=False),
            sa.Column("kind", sa.String(length=40), nullable=False),
            sa.Column("policy_version", sa.String(length=40), nullable=False),
            sa.Column("agreed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_consent_owner", "consents", ["owner", "kind"])


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if insp.has_table("consents"):
        op.drop_index("ix_consent_owner", table_name="consents")
        op.drop_table("consents")
