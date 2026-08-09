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

# 실제 청주 개발 호재(출처 확인). 좌표는 개략 위치(㎞ 단위 참고용) — 정밀 지번 아님.
# 사실만 기재, 집값 상승 단정·투자 권유 금지.
LANDMARKS: list[dict] = [
    {"name": "SK하이닉스 P&T7 (첨단 패키징 팹)", "category": "industry",
     "status": "ongoing", "lat": 36.6805, "lng": 127.4200, "expected_year": 2028,
     "summary": "청주테크노폴리스(흥덕구 외북동)에 AI 메모리용 첨단 패키징 팹 P&T7 착공. "
                "약 19조원 투자, 2028년 완공 목표. 완공 후 약 3,000명 근무 예정.",
     "source_name": "SK하이닉스 뉴스룸", "source_url": "https://news.skhynix.co.kr/skhynix-chungju-pt7/",
     "sort_order": 1},
    {"name": "다목적 방사광가속기 (오창)", "category": "industry",
     "status": "ongoing", "lat": 36.7100, "lng": 127.4400, "expected_year": 2028,
     "summary": "오창에 구축 중인 다목적 방사광가속기. 포항에 이은 국내 두 번째로, "
                "2028년경 본격 가동 목표. 약 6조원 규모의 경제효과가 기대됨.",
     "source_name": "언론보도(inews24)·충북테크노파크", "source_url": "https://m.inews24.com/v/1980077",
     "sort_order": 2},
    {"name": "청주테크노폴리스 산업단지", "category": "industry",
     "status": "ongoing", "lat": 36.6820, "lng": 127.4180, "expected_year": None,
     "summary": "흥덕구 일대 대규모 산업·주거 복합 개발. SK하이닉스 청주캠퍼스(M15·M15X 등) 인접, "
                "산업단지 활성화로 인근 정주 여건·인프라 확충 기대.",
     "source_name": "청주시·나무위키", "source_url": "https://namu.wiki/w/%EC%B2%AD%EC%A3%BC%EC%8B%9C",
     "sort_order": 3},
    {"name": "북청주역세권 개발", "category": "transport",
     "status": "planned", "lat": None, "lng": None, "expected_year": None,
     "summary": "충북선 북청주역 일대 역세권 개발이 예정되어 있음(세부 계획은 진행 상황에 따라 변동).",
     "source_name": "청주시·나무위키", "source_url": "https://namu.wiki/w/%EC%B2%AD%EC%A3%BC%EC%8B%9C",
     "sort_order": 4},
    {"name": "청주 OSCO (오송역세권 전시장)", "category": "commercial",
     "status": "confirmed", "lat": 36.6207, "lng": 127.3271, "expected_year": 2025,
     "summary": "오송역 역세권에 조성된 전시·MICE 시설(청주 OSCO), 2025년 개관. "
                "전시면적 약 1만㎡, KTX·SRT 오송역과 인접.",
     "source_name": "나무위키(청주시)", "source_url": "https://namu.wiki/w/%EC%B2%AD%EC%A3%BC%EC%8B%9C",
     "sort_order": 5},
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
