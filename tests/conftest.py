"""pytest 공통 설정·픽스처.

격리 원칙(운영 안전):
  - 테스트는 항상 '버리는 SQLite 파일'을 쓴다. 아래 환경변수를 import 전에 강제 지정해
    실수로 개발/운영 DB 에 붙는 것을 막는다.
  - MOLIT 키를 비워 네트워크 호출(실수집)을 차단한다. 테스트는 외부 API 를 절대 부르지 않는다.
"""
import os

# ⚠️ app 모듈 import 전에 반드시 먼저 지정(엔진이 import 시점에 생성됨)
os.environ["DATABASE_URL"] = "sqlite:///./_pytest_tmp.db"
os.environ["MOLIT_SERVICE_KEY"] = ""
os.environ["APPLYHOME_SERVICE_KEY"] = ""
os.environ["FINLIFE_API_KEY"] = ""
os.environ["KAKAO_REST_API_KEY"] = ""
os.environ["NAVER_MAP_CLIENT_ID"] = ""
os.environ["NAVER_MAP_CLIENT_SECRET"] = ""
os.environ["AUTH_DEV_LOGIN"] = "true"
os.environ["ADMIN_TOKEN"] = ""
os.environ["RATE_LIMIT_ENABLED"] = "false"   # 테스트는 레이트리밋 비활성(결정성)
os.environ["AUTO_SEED_COMMUTE"] = "false"     # 테스트는 startup 자동 시드 비활성(격리·결정성)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import Base, engine, SessionLocal  # noqa: E402
import app.models  # noqa: E402,F401  (모든 모델 등록)
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./_pytest_tmp.db")
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _clean():
    """각 테스트 후 모든 테이블 비우기 + 집계 캐시 초기화(테스트 간 격리).
    집계 캐시(stat_cached)는 프로세스 전역이라 안 지우면 이전 테스트 결과가 다음 테스트로 샌다
    (특히 data_version 이 DB 기반이라 _clean 후 0 으로 리셋되어 버전키가 재충돌할 수 있음)."""
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    from app.core import cache as _cache
    _cache.cache.clear()
    _cache._dv_cache["v"] = None
    _cache._dv_cache["exp"] = 0.0


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
