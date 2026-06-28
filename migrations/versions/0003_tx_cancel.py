"""transactions: 해제(취소)·정정 반영 컬럼

Revision ID: 0003_tx_cancel
Revises: 0002_baseline
Create Date: 2026-06-18

추가 컬럼:
  - identity_key : 계약 식별(금액 제외) → 정정/해제분 매칭
  - is_canceled  : 해제(취소) 여부 → 집계 제외 (기본 False, 기존행 0 백필)
  - canceled_date: 해제사유발생일
  - corrected_at : 정정으로 금액이 갱신된 시각(감사용)
인덱스: identity_key, (property_type, is_canceled)

무중단: 모두 nullable/default 추가형. 코드 배포 전 본 마이그레이션을 먼저 적용.
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_tx_cancel"
down_revision = "0002_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("transactions")}

    with op.batch_alter_table("transactions") as batch:
        if "identity_key" not in cols:
            batch.add_column(sa.Column("identity_key", sa.String(length=220), nullable=True))
        if "is_canceled" not in cols:
            batch.add_column(sa.Column("is_canceled", sa.Boolean(),
                                       nullable=False, server_default=sa.false()))
        if "canceled_date" not in cols:
            batch.add_column(sa.Column("canceled_date", sa.Date(), nullable=True))
        if "corrected_at" not in cols:
            batch.add_column(sa.Column("corrected_at", sa.DateTime(), nullable=True))

    # 기존 행 백필(혹시 NULL 로 들어온 경우 안전화) — PG/SQLite 공통 boolean 리터럴(false)
    op.execute("UPDATE transactions SET is_canceled = false WHERE is_canceled IS NULL")

    existing_idx = {i["name"] for i in insp.get_indexes("transactions")}
    if "ix_transactions_identity_key" not in existing_idx:
        op.create_index("ix_transactions_identity_key", "transactions", ["identity_key"])
    if "ix_tx_active" not in existing_idx:
        op.create_index("ix_tx_active", "transactions", ["property_type", "is_canceled"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_idx = {i["name"] for i in insp.get_indexes("transactions")}
    if "ix_tx_active" in existing_idx:
        op.drop_index("ix_tx_active", table_name="transactions")
    if "ix_transactions_identity_key" in existing_idx:
        op.drop_index("ix_transactions_identity_key", table_name="transactions")
    with op.batch_alter_table("transactions") as batch:
        for col in ("corrected_at", "canceled_date", "is_canceled", "identity_key"):
            batch.drop_column(col)
