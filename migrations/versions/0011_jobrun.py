"""monitoring: 배치 작업 실행 이력 테이블

Revision ID: 0011_jobrun
Revises: 0010_push
Create Date: 2026-06-21

추가형(additive). 수집/지오코딩 등 배치 실행 이력(관측성).
inspect 가드로 멱등(fresh DB는 create_all 로 이미 생성됨). 타입 portable.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0011_jobrun"
down_revision = "0010_push"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("job_runs"):
        op.create_table(
            "job_runs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=40), nullable=False),
            sa.Column("status", sa.String(length=12), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("stats", sa.JSON(), nullable=True),
            sa.Column("error", sa.String(length=500), nullable=True),
        )
        op.create_index("ix_jobrun_name_started", "job_runs", ["name", "started_at"])


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if insp.has_table("job_runs"):
        op.drop_table("job_runs")
