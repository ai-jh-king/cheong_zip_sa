"""push: 웹푸시(VAPID) 구독 테이블

Revision ID: 0010_push
Revises: 0009_commute
Create Date: 2026-06-21

추가형(additive). 브라우저 웹푸시 구독 저장. endpoint 고유.
inspect 가드로 멱등(fresh DB는 create_all 로 이미 생성됨). 타입 portable.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0010_push"
down_revision = "0009_commute"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("push_subscriptions"):
        op.create_table(
            "push_subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("device_id", sa.String(length=64), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=True),
            sa.Column("channel", sa.String(length=12), nullable=False, server_default="webpush"),
            sa.Column("endpoint", sa.String(length=500), nullable=False),
            sa.Column("p256dh", sa.String(length=200), nullable=True),
            sa.Column("auth", sa.String(length=100), nullable=True),
            sa.Column("token", sa.String(length=400), nullable=True),
            sa.Column("user_agent", sa.String(length=200), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("last_ok_at", sa.DateTime(), nullable=True),
            sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.UniqueConstraint("endpoint", name="uq_push_endpoint"),
        )
        op.create_index("ix_push_device", "push_subscriptions", ["device_id"])
        op.create_index("ix_push_account", "push_subscriptions", ["account_id"])


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if insp.has_table("push_subscriptions"):
        op.drop_table("push_subscriptions")
