"""create listings table

Revision ID: 0001_listings
Revises:
Create Date: 2026-06-18

등록 매물(UGC) 테이블. 기존 테이블들은 dev에서 create_all 로 생성되므로
이 마이그레이션은 listings 만 추가한다. 이미 존재하면 건너뛴다(멱등).
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_listings"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "listings" in insp.get_table_names():
        return
    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("poster_role", sa.String(length=20), nullable=False, server_default="user"),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("deal_type", sa.String(length=10), nullable=False),
        sa.Column("property_type", sa.String(length=20), nullable=False),
        sa.Column("lawd_cd", sa.String(length=5), nullable=False),
        sa.Column("dong_name", sa.String(length=40), nullable=True),
        sa.Column("complex_name", sa.String(length=120), nullable=True),
        sa.Column("address_detail", sa.String(length=200), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("exclusive_area", sa.Float(), nullable=True),
        sa.Column("supply_area", sa.Float(), nullable=True),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("total_floor", sa.Integer(), nullable=True),
        sa.Column("rooms", sa.Integer(), nullable=True),
        sa.Column("baths", sa.Integer(), nullable=True),
        sa.Column("direction", sa.String(length=10), nullable=True),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("deposit", sa.Integer(), nullable=True),
        sa.Column("monthly_rent", sa.Integer(), nullable=True),
        sa.Column("maintenance_fee", sa.Integer(), nullable=True),
        sa.Column("maintenance_items", sa.String(length=200), nullable=True),
        sa.Column("move_in_date", sa.String(length=40), nullable=True),
        sa.Column("approval_date", sa.String(length=40), nullable=True),
        sa.Column("options", sa.String(length=200), nullable=True),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("photos", sa.JSON(), nullable=True),
        sa.Column("agent_office", sa.String(length=120), nullable=True),
        sa.Column("agent_name", sa.String(length=40), nullable=True),
        sa.Column("agent_reg_no", sa.String(length=40), nullable=True),
        sa.Column("agent_phone", sa.String(length=40), nullable=True),
        sa.Column("agent_address", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("is_sample", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_listing_region_deal", "listings", ["lawd_cd", "deal_type"])
    op.create_index("ix_listing_created", "listings", ["created_at"])
    op.create_index("ix_listings_device_id", "listings", ["device_id"])


def downgrade():
    op.drop_index("ix_listings_device_id", table_name="listings")
    op.drop_index("ix_listing_created", table_name="listings")
    op.drop_index("ix_listing_region_deal", table_name="listings")
    op.drop_table("listings")
