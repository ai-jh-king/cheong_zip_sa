"""부하 감사 인덱스 3종 — 핫패스 풀스캔 제거.

- ix_tx_complex_lawd: 단지상세·호가검증·급매·매물신호가 complex_name 등가조건 풀스캔(H2)
- ix_places_lat_lng: 단지상세·지도 bbox 조회 풀스캔(M4)
- ix_listing_account: 내 매물 필터·로그인 매물 흡수(L1)
"""
from alembic import op
from sqlalchemy import inspect

revision = "0021_perf_indexes"
down_revision = "0020_agg_snapshot"
branch_labels = None
depends_on = None

_INDEXES = [
    ("transactions", "ix_tx_complex_lawd", ["complex_name", "lawd_cd"]),
    ("places", "ix_places_lat_lng", ["lat", "lng"]),
    ("listings", "ix_listing_account", ["account_id"]),
]


def upgrade() -> None:
    insp = inspect(op.get_bind())
    for table, name, cols in _INDEXES:
        if not insp.has_table(table):
            continue
        existing = {ix["name"] for ix in insp.get_indexes(table)}
        if name not in existing:
            op.create_index(name, table, cols)


def downgrade() -> None:
    for table, name, _ in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
