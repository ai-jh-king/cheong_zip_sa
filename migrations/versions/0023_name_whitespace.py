"""단지명 내부 공백 제거 — 같은 단지 이중 집계 해소(실사고 11개 단지).

원인: MOLIT 매매/전월세·오피스텔 API 가 같은 단지를 '강서 베리굿'/'강서베리굿'처럼
다르게 표기 → 별개 단지로 쪼개져 시세·목록이 이중 표출. 동·건축년도 대조로 동일 단지 실증됨.
조치: ①transactions.complex_name 공백 제거 ②complexes 는 공백 제거 후 충돌 시
지오코딩(lat 보유) 우선 1행만 유지. (수집단 정규화는 normalize.py 에 동시 적용)
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_name_whitespace"
down_revision = "0022_guides"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # 1) 거래 테이블: 이름 공백 제거(dedup_key 는 불변 문자열이라 무영향)
    conn.execute(sa.text(
        "UPDATE transactions SET complex_name = REPLACE(complex_name, ' ', '') "
        "WHERE complex_name LIKE '% %'"))
    # 2) 단지 테이블: 공백 제거 시 (name,lawd_cd) 충돌 → 좌표 보유 행 우선, 그중 id 최소만 유지
    rows = conn.execute(sa.text(
        "SELECT REPLACE(name,' ','') AS nn, lawd_cd FROM complexes "
        "GROUP BY REPLACE(name,' ',''), lawd_cd HAVING COUNT(*) > 1")).fetchall()
    for nn, lawd in rows:
        dup = conn.execute(sa.text(
            "SELECT id, lat FROM complexes WHERE REPLACE(name,' ','')=:nn AND lawd_cd=:lawd "
            "ORDER BY (lat IS NULL), id"), {"nn": nn, "lawd": lawd}).fetchall()
        keep = dup[0][0]
        drop_ids = [r[0] for r in dup[1:]]
        if drop_ids:
            conn.execute(sa.text("DELETE FROM complexes WHERE id = ANY(:ids)")
                         if conn.dialect.name == "postgresql" else
                         sa.text(f"DELETE FROM complexes WHERE id IN ({','.join(map(str, drop_ids))})"),
                         {"ids": drop_ids} if conn.dialect.name == "postgresql" else {})
        conn.execute(sa.text("UPDATE complexes SET name=:nn WHERE id=:id"),
                     {"nn": nn, "id": keep})
    # 3) 잔여(충돌 없던) 단지명도 공백 제거
    conn.execute(sa.text(
        "UPDATE complexes SET name = REPLACE(name, ' ', '') WHERE name LIKE '% %'"))


def downgrade() -> None:
    pass   # 공백 제거는 비가역(원 표기 미보존) — raw_payload 에 원본 잔존
