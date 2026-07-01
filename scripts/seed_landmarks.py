"""개발 호재(Landmark) 시드 — '구조만 먼저, 데이터는 나중에'.

사용법: 아래 LANDMARKS 리스트에 호재를 채운 뒤  ->  python -m scripts.seed_landmarks
(이름 기준 upsert. 다시 실행하면 갱신).

⚠️ 왜곡 없음 규칙(반드시 지킬 것):
  - status: "confirmed"(확정) / "ongoing"(추진) / "planned"(계획) 중 사실에 맞게.
  - summary: '사실'만. 예) "2029년 준공 목표, 사업비 1.16조원". 집값 상승 단정·투자 권유 금지.
  - source_name/source_url: 출처 필수(보도자료·관 고시 등). 출처 없으면 등록하지 말 것.
  - lat/lng: 정확한 좌표(없으면 지도/거리 제외). category: industry/transport/commercial/residential/public.

예시(참고용, 실제 등록 전 출처·좌표·단계 재확인):
  {"name":"다목적 방사광가속기","category":"industry","status":"ongoing","lat":36.71,"lng":127.43,
   "expected_year":2029,"summary":"오창테크노폴리스 내 구축, 사업비 약 1.16조원(준공 목표 2029)",
   "source_name":"충북도 보도자료","source_url":"https://...","sort_order":1},
"""
import sys
import logging
from datetime import datetime

from app.core.config import get_settings
from app.db.session import init_db, SessionLocal
from app.models import Landmark

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger("seed_landmarks")

# 여기에 호재를 채우세요(지금은 비어 있음 → 0건).
LANDMARKS: list[dict] = [
]


def main() -> int:
    init_db()
    if not LANDMARKS:
        print("등록할 호재가 없습니다. scripts/seed_landmarks.py 의 LANDMARKS 에 출처·좌표와 함께 채우세요.")
        return 0
    db = SessionLocal()
    created = updated = 0
    try:
        for d in LANDMARKS:
            if not d.get("name"):
                continue
            ex = db.query(Landmark).filter(Landmark.name == d["name"]).one_or_none()
            if ex:
                for k, v in d.items():
                    setattr(ex, k, v)
                ex.updated_at = datetime.utcnow()
                updated += 1
            else:
                db.add(Landmark(**d))
                created += 1
        db.commit()
        print(f"호재 시드 완료 — 신규 {created} · 갱신 {updated}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
