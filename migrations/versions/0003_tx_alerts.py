"""transaction alerts: notifications 컬럼 + app_meta

Revision ID: 0003_tx_alerts
Revises: 0002_baseline
Create Date: 2026-06-19

- notifications 에 transaction 알림용 단지 참조 컬럼 추가(complex_name/lawd_cd/property_type).
- app_meta(key/value) 신설: 알림 커서(notify_last_tx_id) 등 운영 워터마크 영속 저장.
모두 추가형(additive) — 기존 데이터 영향 없음. SQLite/PostgreSQL 공통 ADD COLUMN.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0003_tx_alerts"
down_revision = "0003_tx_cancel"
branch_labels = None
depends_on = None

_NOTIF_COLS = [
    ("complex_name", sa.String(length=120)),
    ("lawd_cd", sa.String(length=5)),
    ("property_type", sa.String(length=20)),
]


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    existing = {c["name"] for c in insp.get_columns("notifications")} if insp.has_table("notifications") else set()
    for name, type_ in _NOTIF_COLS:
        if name not in existing:
            op.add_column("notifications", sa.Column(name, type_, nullable=True))
    if not insp.has_table("app_meta"):
        op.create_table(
            "app_meta",
            sa.Column("key", sa.String(length=80), primary_key=True),
            sa.Column("value", sa.String(length=200), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if insp.has_table("app_meta"):
        op.drop_table("app_meta")
    existing = {c["name"] for c in insp.get_columns("notifications")} if insp.has_table("notifications") else set()
    for name, _ in _NOTIF_COLS:
        if name in existing:
            op.drop_column("notifications", name)
