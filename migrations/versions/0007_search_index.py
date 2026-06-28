"""검색 성능: pg_trgm 인덱스(부분일치 LIKE 가속)

Revision ID: 0007_search_index
Revises: 0006_gongsi
Create Date: 2026-06-19

검색은 `LIKE '%q%'`(부분일치)라 일반 B-Tree 인덱스를 타지 못한다.
PostgreSQL 에서는 pg_trgm 확장 + GIN(trgm) 인덱스로 부분일치도 인덱스 검색이 된다.
SQLite 등은 해당 기능이 없어 건너뛴다(개발용 소규모 데이터는 풀스캔으로 충분).
"""
from alembic import op

revision = "0007_search_index"
down_revision = "0006_gongsi"
branch_labels = None
depends_on = None

# (인덱스명, 테이블, 컬럼)
_TRGM = [
    ("ix_tx_cxname_trgm", "transactions", "complex_name"),
    ("ix_tx_dong_trgm", "transactions", "dong_name"),
    ("ix_listing_title_trgm", "listings", "title"),
    ("ix_listing_cxname_trgm", "listings", "complex_name"),
    ("ix_listing_dong_trgm", "listings", "dong_name"),
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # pg_trgm 미지원 DB는 건너뜀
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for name, table, col in _TRGM:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON {table} "
            f"USING gin ({col} gin_trgm_ops)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for name, _, _ in _TRGM:
        op.execute(f"DROP INDEX IF EXISTS {name}")
