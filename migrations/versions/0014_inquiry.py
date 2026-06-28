"""inquiries(매물 문의/리드) 테이블 추가 — 첫 매출(B2B) 기반

Revision ID: 0014_inquiry
Revises: 0013_listing_views
Create Date: 2026-06-25

신규 테이블(additive)·멱등(inspect 가드). 소유자 비정규화 컬럼으로 대시보드 '내 리드' 조회.
연락처(contact)는 민감정보 — 소유자만 열람, 동의(consent) 필수(앱 레벨).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0014_inquiry"
down_revision = "0013_listing_views"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if insp.has_table("inquiries"):
        return
    op.create_table(
        "inquiries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("listing_id", sa.Integer(), nullable=False, index=True),
        sa.Column("owner_account_id", sa.Integer(), nullable=True),
        sa.Column("owner_device_id", sa.String(length=64), nullable=True),
        sa.Column("inquirer_device_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("name", sa.String(length=40), nullable=True),
        sa.Column("contact", sa.String(length=120), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new"),
        sa.Column("consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_inquiry_owner_acc", "inquiries", ["owner_account_id"])
    op.create_index("ix_inquiry_owner_dev", "inquiries", ["owner_device_id"])
    op.create_index("ix_inquiry_listing", "inquiries", ["listing_id"])


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("inquiries"):
        return
    for ix in ("ix_inquiry_owner_acc", "ix_inquiry_owner_dev", "ix_inquiry_listing"):
        try:
            op.drop_index(ix, table_name="inquiries")
        except Exception:
            pass
    op.drop_table("inquiries")
