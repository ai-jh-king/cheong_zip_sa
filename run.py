"""
한 번의 실행으로: (필요시 의존성 자동설치) → DB 생성 → 데이터 수집 → API+UI 서빙 → 브라우저 자동 오픈.

사용법:
  python run.py            # 키 있으면 실수집(live), 없으면 모의데이터(fixtures)
  python run.py --refresh  # 기존 적재 무시하고 다시 수집
  python run.py --no-install  # 의존성 자동설치 건너뛰기

이미 데이터가 있으면 수집을 건너뛴다(중복 호출 방지). --refresh 로 강제 재수집.
"""
import sys
import subprocess


def ensure_deps() -> None:
    """필수 패키지가 없으면 requirements.txt 로 자동 설치 (윈도우 .bat 불필요)."""
    if "--no-install" in sys.argv:
        return
    try:
        import fastapi, uvicorn, sqlalchemy, pydantic_settings, httpx  # noqa: F401
        return
    except ImportError:
        print("필수 패키지를 설치합니다… (최초 1회, 잠시 소요)")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"]
        )


ensure_deps()

import logging
import threading
import webbrowser

import uvicorn
from sqlalchemy import select, func

from app.core.config import get_settings
from app.db.session import init_db, SessionLocal
from app.models import Transaction
from app.pipeline.collect import collect_live, collect_from_fixtures
from app.sources.molit.client import MolitAuthError

logging.basicConfig(level=get_settings().log_level,
                    format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("run")

HOST, PORT = "127.0.0.1", 8000


def _maybe_geocode(db) -> None:
    """수집 후 좌표 없는 단지를 자동 지오코딩(네이버/카카오 키 있을 때만).
    이미 좌표가 있는 단지는 내부에서 건너뜀 → 재시작 시 비용 거의 없음. 키 없으면 조용히 패스."""
    s = get_settings()
    if not s.auto_geocode:
        return
    has_key = (s.naver_map_client_id and s.naver_map_client_secret) or s.kakao_rest_api_key
    if not has_key:
        return
    try:
        from app.services.geocode import run_geocode
        res = run_geocode(db, limit=(s.geocode_seed_limit or None))
        log.info("지오코딩(자동): %s", res)
    except Exception as e:  # noqa
        log.warning("자동 지오코딩 건너뜀: %s", e)


def seed(refresh: bool) -> None:
    init_db()
    s = get_settings()
    with SessionLocal() as db:
        # 예시 매물(UGC) — 비어있을 때만 데모 3건 적재(is_sample=True, '예시' 배지)
        try:
            from app.models import Listing
            from app.data.sample_listings import SAMPLE_LISTINGS
            if not (db.scalar(select(func.count()).select_from(Listing)) or 0):
                for L in SAMPLE_LISTINGS:
                    db.add(Listing(is_sample=True, **L))
                db.commit()
                log.info("예시 매물 %s건 적재(is_sample)", len(SAMPLE_LISTINGS))
        except Exception as e:  # noqa
            log.warning("예시 매물 적재 건너뜀: %s", e)
        # 예시 게시글(커뮤니티) — 비어있을 때만
        try:
            from app.models import Post, Comment
            from app.data.sample_posts import SAMPLE_POSTS, SAMPLE_COMMENTS
            if not (db.scalar(select(func.count()).select_from(Post)) or 0):
                posts = []
                for P in SAMPLE_POSTS:
                    p = Post(is_sample=True, **P)
                    db.add(p)
                    posts.append(p)
                db.flush()
                for C in SAMPLE_COMMENTS:
                    idx = C.pop("post_idx", 0)
                    db.add(Comment(is_sample=True, post_id=posts[idx].id, **C))
                db.commit()
                log.info("예시 게시글 %s건 적재(is_sample)", len(SAMPLE_POSTS))
        except Exception as e:  # noqa
            log.warning("예시 게시글 적재 건너뜀: %s", e)
        count = db.scalar(select(func.count()).select_from(Transaction)) or 0
        if count and not refresh:
            log.info("이미 %s건 적재됨 → 수집 건너뜀 (강제 재수집: python run.py --refresh)", count)
            _maybe_geocode(db)
            return
        if s.molit_enabled:
            log.info("MOLIT 키 감지 → 실거래 수집(live)…")
            try:
                res = collect_live(db)
                log.info("실수집 완료: %s", res)
                _maybe_geocode(db)
                return
            except MolitAuthError as e:
                print("\n" + "!" * 60)
                print("  공공데이터 인증 거부(401/미등록) — 실수집을 건너뜁니다.")
                print(str(e))
                print("  지금은 모의데이터로 화면을 띄웁니다. 위 항목 해결 후 'python run.py --refresh'.")
                print("!" * 60 + "\n")
            except Exception as e:  # noqa
                log.warning("live 수집 실패(%s) → 모의데이터로 폴백", e)
        else:
            log.info("MOLIT 키 없음 → 모의데이터(fixtures) 적재 (실시세 아님)")
        res = collect_from_fixtures(db)
        log.info("적재 완료: %s", res)
        _maybe_geocode(db)


def main() -> int:
    refresh = "--refresh" in sys.argv
    seed(refresh)

    url = f"http://{HOST}:{PORT}"
    print("\n" + "=" * 56)
    print(f"  청주 시세 대시보드 실행 중 →  {url}")
    print(f"  API 문서(Swagger)        →  {url}/docs")
    print("  종료: Ctrl+C")
    print("=" * 56 + "\n")
    threading.Timer(1.3, lambda: webbrowser.open(url)).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
