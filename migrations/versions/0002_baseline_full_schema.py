"""baseline: 전체 스키마 일원화

Revision ID: 0002_baseline
Revises: 0001_listings
Create Date: 2026-06-18

목적: 그동안 dev 의 create_all + _ensure_columns 에만 의존하던 테이블들을
Alembic 권위 소스로 편입한다. 운영/스테이징은 이제 `alembic upgrade head` 만으로
전체 스키마가 재현된다.

설계 원칙(왜곡/드리프트 방지):
  - upgrade 는 Base.metadata 에서 직접 생성(create_all, checkfirst=True).
    → 마이그레이션이 모델과 100% 일치(컬럼/인덱스/제약 전사 오류 0), 그리고 멱등.
    → 이미 존재하는 테이블(예: dev 에서 create_all 로 만든 것, 0001 의 listings)은 건너뜀.
  - 신규 컬럼(posts.images/complex_name/property_type, comments.parent_id)도
    모델 메타데이터에 반영돼 있으므로, 빈 DB 에서는 한 번에 올바르게 생성된다.
    (기존 DB 의 컬럼 추가는 run-time 의 _ensure_columns 가 계속 안전망 역할)
  - 이후 스키마 변경은 `alembic revision --autogenerate` 로 세분화된 DDL 을 생성한다
    (env.py 의 target_metadata = Base.metadata 가 diff 기준).

downgrade: 베이스라인이므로 0001(listings) 이전 상태로의 정밀 롤백은 지원하지 않는다.
  이 리비전이 생성 대상으로 삼는 비-listings 테이블만 드롭한다(테이블명 기준, 저위험).
"""
from alembic import op
from sqlalchemy import inspect

from app.db.session import Base
import app.models  # noqa: F401  (모든 모델 등록)


revision = "0002_baseline"
down_revision = "0001_listings"
branch_labels = None
depends_on = None

# 0001 에서 만든 listings 를 제외한, 이 베이스라인이 책임지는 테이블 목록.
# (downgrade 전용. upgrade 는 metadata 전체를 checkfirst 로 생성하므로 목록 불필요)
_BASELINE_TABLES = [
    # 자식/참조부터 → 부모 순서로 드롭(이 프로젝트는 실제 FK 제약이 거의 없어 순서 영향 적음)
    "bookmarks", "notifications", "report_logs", "post_likes",
    "comments", "posts",
    "saved_searches", "recent_views", "user_prefs", "favorites",
    "device_links", "accounts",
    "transactions", "complexes", "regions",
]


def upgrade() -> None:
    bind = op.get_bind()
    # 모델 메타데이터 그대로 생성(존재하면 건너뜀) → 모델과 100% 일치 + 멱등
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    existing = set(insp.get_table_names())
    for tbl in _BASELINE_TABLES:
        if tbl in existing:
            op.drop_table(tbl)
