"""검색 가속 — pg_trgm GIN 인덱스 (선두 와일드카드 LIKE 풀스캔 개선)

Revision ID: 0016_search_trgm
Revises: 0015_subscription
Create Date: 2026-06-26

배경: 통합 검색(`/search`)은 `complex_name/dong_name/title LIKE '%q%'`(선두 와일드카드)라
일반 B-tree 인덱스를 못 탄다. PostgreSQL의 pg_trgm GIN 인덱스(`gin_trgm_ops`)는
`LIKE '%q%'`·`ILIKE`를 인덱스로 가속한다(코드 변경 불필요 — 기존 .like() 그대로 사용).

- **PostgreSQL 전용**: SQLite 등 다른 dialect는 no-op(폴백=스캔, 개발/소규모엔 무방).
- 멱등(IF NOT EXISTS). 대형 테이블에서 무중단이 필요하면 운영자가 CONCURRENTLY로 별도 생성 가능
  (마이그레이션은 트랜잭션 안에서 돌아 CONCURRENTLY 불가 → 여기선 일반 생성).
- 트라이그램 특성상 3글자 이상에서 선택도가 좋다(1~2글자 검색은 여전히 스캔에 가깝지만
  다른 WHERE 필터·limit로 제한됨).
"""
from alembic import op

revision = "0016_search_trgm"
down_revision = "0015_subscription"
branch_labels = None
depends_on = None

_INDEXES = [
    ("ix_tx_complex_trgm", "transactions", "complex_name"),
    ("ix_tx_dong_trgm", "transactions", "dong_name"),
    ("ix_listing_title_trgm", "listings", "title"),
    ("ix_listing_complex_trgm", "listings", "complex_name"),
    ("ix_listing_dong_trgm", "listings", "dong_name"),
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # SQLite 등은 스킵(LIKE 스캔 폴백)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for name, table, col in _INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON {table} USING gin ({col} gin_trgm_ops)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for name, _table, _col in _INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
