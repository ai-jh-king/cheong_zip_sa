"""생활·교육·운동 시설(Place) 수집·적재 CLI.

사용법:
  python -m scripts.collect_places academy     # 학원·교습소
  python -m scripts.collect_places sports      # 체육시설(체육관·수영장·풋살 등)
  python -m scripts.collect_places medical     # 의료기관(병원·의원·약국) — 좌표 EPSG:5174 변환(pyproj)
  python -m scripts.collect_places library     # 도서관
  python -m scripts.collect_places daycare     # 어린이집·유치원
  python -m scripts.collect_places all         # 학원+체육+의료 한 번에

동작: 공공데이터 → 정규화 → Place upsert(source_key 기준 중복 방지). 좌표 없는 행도 저장(거리계산만 제외).
키 없으면 0건(앱은 빈 섹션, 안전). 적재 후 좌표 없는 학원은 scripts.geocode 로 보강 가능.
"""
import sys
import logging

from app.core.config import get_settings
from app.db.session import init_db, SessionLocal
from app.models import Place
from app.sources.academy import fetch_academies
from app.sources.sports import fetch_sports
from app.sources.medical import fetch_medical
from app.sources.library import fetch_libraries
from app.sources.daycare import fetch_daycares

logging.basicConfig(level=get_settings().log_level,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("collect_places")


def _upsert(db, rows: list[dict]) -> tuple[int, int]:
    """source_key 기준 upsert. (신규, 갱신) 반환."""
    created = updated = 0
    for r in rows:
        key = r.get("source_key")
        if not key:
            continue
        existing = db.query(Place).filter(Place.source_key == key).one_or_none()
        if existing:
            for f in ("name", "category", "subcategory", "course", "road_address",
                      "lawd_cd", "dong_name", "lat", "lng", "tuition", "status", "attrs"):
                if f in r and r[f] is not None:
                    setattr(existing, f, r[f])
            updated += 1
        else:
            db.add(Place(**r))
            created += 1
    db.commit()
    return created, updated


def collect_academy() -> int:
    rows = fetch_academies()
    if not rows:
        print("학원 수집 0건(키 미설정이거나 응답 없음). ACADEMY_SERVICE_KEY 또는 MOLIT_SERVICE_KEY 확인.")
        return 0
    db = SessionLocal()
    try:
        created, updated = _upsert(db, rows)
        print(f"학원 적재 완료 — 신규 {created} · 갱신 {updated} (총 {len(rows)}건 정규화)")
    finally:
        db.close()
    return 0


def _run(label: str, fetch) -> int:
    rows = fetch()
    if not rows:
        print(f"{label} 수집 0건(키 미설정이거나 응답 없음).")
        return 0
    db = SessionLocal()
    try:
        created, updated = _upsert(db, rows)
        print(f"{label} 적재 완료 — 신규 {created} · 갱신 {updated} (총 {len(rows)}건)")
    finally:
        db.close()
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "help"
    init_db()
    if cmd == "academy":
        return collect_academy()
    if cmd == "sports":
        return _run("체육시설", fetch_sports)
    if cmd == "medical":
        return _run("의료기관", fetch_medical)
    if cmd == "library":
        return _run("도서관", fetch_libraries)
    if cmd == "daycare":
        return _run("어린이집·유치원", fetch_daycares)
    if cmd == "all":
        collect_academy()
        _run("체육시설", fetch_sports)
        _run("의료기관", fetch_medical)
        _run("도서관", fetch_libraries)
        _run("어린이집·유치원", fetch_daycares)
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
