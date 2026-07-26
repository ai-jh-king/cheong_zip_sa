"""집사 도감 — 첫 시리즈 + 초기 편 시드(멱등). 이후 편은 admin API 로 발행(주 1편 큐레이션).

사용:
  python -m scripts.seed_guides

편 본문은 app/data/guides/*.md (레포에 보존 — 검수 이력·재배포 재현성).
멱등: 같은 제목의 편이 이미 있으면 건너뜀(운영에서 수정한 본문을 덮어쓰지 않음).
"""
import logging
from pathlib import Path

from app.db.session import init_db, SessionLocal
from app.models import Guide, GuideSeries

logging.basicConfig(level="INFO", format="%(levelname)s: %(message)s")
log = logging.getLogger("seed_guides")

GUIDES_DIR = Path(__file__).resolve().parents[1] / "app" / "data" / "guides"

SERIES = [
    dict(key="cheongju", name="집사가 알려주는 청주",
         description="청주에서 잘 살고 싶은 사람을 위한 청집사의 실사용 안내서",
         cover_emoji="🏘", sort_order=1),
    # 후속 시리즈(계약/대출/안전/이사/청약)는 콘텐츠가 준비될 때 추가.
]

# (시리즈, 제목, md파일, 이모지, 순서) — 본문 수치는 발행 시점 실데이터 조회 기반(왜곡 없음)
EPISODES = [
    ("cheongju", "SK하이닉스 청주캠퍼스로 출퇴근한다면 — 데이터로 본 근처 단지들",
     "cheongju_ep1_sk_hynix.md", "🏭", 1),
    ("cheongju", "청주 4개 구, 숫자로 비교해 봤습니다",
     "cheongju_ep2_gu_compare.md", "🗺", 2),
    ("cheongju", "전세 계약 전, 이것만은 확인하세요 — 집사의 체크리스트",
     "cheongju_ep3_jeonse_check.md", "🛡", 3),
    ("cheongju", "신축 vs 구축, 청주에서 가격 차이는 얼마나 날까",
     "cheongju_ep4_age_price.md", "🧱", 4),
    ("cheongju", "청주 개발 이슈 총정리 — 사실과 출처만",
     "cheongju_ep5_landmarks.md", "🏗", 5),
    ("cheongju", "부동산 거래가 처음이라면 — 계약 전 확인 10가지",
     "cheongju_ep6_first_deal.md", "📝", 6),
]


def run() -> dict:
    init_db()
    s_created = g_created = 0
    with SessionLocal() as db:
        for s in SERIES:
            if not db.get(GuideSeries, s["key"]):
                db.add(GuideSeries(**s))
                s_created += 1
        for series_key, title, fname, emoji, order in EPISODES:
            if db.query(Guide).filter(Guide.series_key == series_key,
                                      Guide.title == title).first():
                continue
            path = GUIDES_DIR / fname
            if not path.exists():
                log.warning("본문 파일 없음: %s — 건너뜀", fname)
                continue
            db.add(Guide(series_key=series_key, title=title,
                         body_md=path.read_text(encoding="utf-8"),
                         cover_emoji=emoji, sort_order=order, is_published=True))
            g_created += 1
        db.commit()
    return {"series_created": s_created, "guides_created": g_created}


if __name__ == "__main__":
    log.info("결과: %s", run())
