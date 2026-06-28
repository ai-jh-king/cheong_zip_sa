"""subscriptions(구독/결제) 테이블 추가 — 결제 시스템(기본 OFF)

Revision ID: 0015_subscription
Revises: 0014_inquiry
Create Date: 2026-06-25

신규 테이블(additive)·멱등(inspect 가드). feature_billing OFF가 기본이라 테이블이 있어도
권한 게이팅은 비활성(현재와 동일). 권한 판정은 entitlement.is_premium.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0015_subscription"
down_revision = "0014_inquiry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if insp.has_table("subscriptions"):
        return
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("plan", sa.String(length=40), nullable=False, server_default="agent_pro"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("provider", sa.String(length=20), nullable=False, server_default="mock"),
        sa.Column("provider_ref", sa.String(length=120), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_sub_account", "subscriptions", ["account_id"])
    op.create_index("ix_sub_status", "subscriptions", ["status"])


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("subscriptions"):
        return
    for ix in ("ix_sub_account", "ix_sub_status"):
        try:
            op.drop_index(ix, table_name="subscriptions")
        except Exception:
            pass
    op.drop_table("subscriptions")
