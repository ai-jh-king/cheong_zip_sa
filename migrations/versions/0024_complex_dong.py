"""complexes.dong 추가 — 같은 구 동명(同名) 단지 분리(지도 마커 병합 왜곡 교정).

원인: Complex 가 (name, lawd_cd) 단위라, 같은 구에 이름이 같은 서로 다른 단지
(예: 흥덕구 '대원' 가경동/복대동, '세원' 복대동/봉명동/운천동 — 23그룹)가 1행으로
합쳐짐 → 지도 마커 좌표·동 표기가 임의로 섞이고 시세 중앙값도 두 단지가 혼합.
조치: ①dong 컬럼 추가 ②거래에서 동이 유일하게 확인되는 단지만 dong 백필(추측 금지)
③모호(복수 동) 단지는 dong=NULL 유지 — 이후 지오코딩이 동 단위 행을 새로 만들어
동 포함 질의로 좌표를 채울 때까지 지도에서 제외(왜곡 없음).
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_complex_dong"
down_revision = "0023_name_whitespace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("complexes", sa.Column("dong", sa.String(40), nullable=True))
    # 백필: 거래 기록상 법정동이 정확히 1개인 단지만 그 동으로 확정(복수 동=NULL 유지).
    # 상관 서브쿼리의 HAVING COUNT(DISTINCT)=1 은 SQLite/PostgreSQL 공통 동작.
    op.get_bind().execute(sa.text(
        "UPDATE complexes SET dong = ("
        "  SELECT MIN(t.dong_name) FROM transactions t"
        "  WHERE t.complex_name = complexes.name AND t.lawd_cd = complexes.lawd_cd"
        "    AND t.dong_name IS NOT NULL"
        "  HAVING COUNT(DISTINCT t.dong_name) = 1"
        ") WHERE dong IS NULL"))


def downgrade() -> None:
    op.drop_column("complexes", "dong")
