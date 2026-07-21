"""agg_snapshot — 일일 집계 스냅샷(프리컴퓨트) 저장 테이블.

무거운 board/ranking 집계를 수집 직후 1회 구워 저장 → 웹은 읽기 1회로 첫 로드 즉시 응답.
payload 는 대형 JSON 이라 Text(무제한). data_version 으로 라이브 폴백 판정."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0020_agg_snapshot"
down_revision = "0019_post_resident"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("agg_snapshot"):
        op.create_table(
            "agg_snapshot",
            sa.Column("key", sa.String(length=120), primary_key=True, nullable=False),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.Column("data_version", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("baked_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("agg_snapshot")
