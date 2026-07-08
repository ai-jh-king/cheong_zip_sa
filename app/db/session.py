"""DB 세션/엔진. DATABASE_URL 미설정 시 SQLite 로 자동 동작."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()
_url = settings.effective_database_url

if _url.startswith("sqlite"):
    # 로컬 개발: SQLite(설치 불필요). 멀티스레드 접근 허용.
    engine = create_engine(_url, echo=False,
                           connect_args={"check_same_thread": False},
                           pool_pre_ping=True)
else:
    # 운영: PostgreSQL 등. 커넥션 풀 + 끊긴 커넥션 자동 감지/재활용.
    engine = create_engine(_url, echo=False, pool_pre_ping=True,
                           pool_size=5, max_overflow=10, pool_recycle=1800)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """스키마 준비.

    개발(dev, 보통 SQLite): create_all 로 빠르게 전체 테이블 생성 + _ensure_columns 로
      기존 DB 에 신규 컬럼 보강(빠른 시작·일회용 DB 에 적합).
    운영/스테이징(PostgreSQL): create_all 대신 Alembic 을 권위 소스로 사용한다.
      → 배포 시 `python -m scripts.db_upgrade`(= alembic upgrade head).
      베이스라인(0002)이 Base.metadata 에서 생성되므로 create_all 결과와 스키마가 동일.
      기존 create_all DB 를 Alembic 이력에 편입하려면 `python -m scripts.db_upgrade stamp head`.
    """
    from app import models  # noqa: F401  (모델 등록)
    if engine.dialect.name == "sqlite":
        # 로컬 개발(SQLite): 빠른 전체 생성 + 신규 컬럼 보강
        Base.metadata.create_all(bind=engine)
        _ensure_columns()
    # 운영(PostgreSQL 등): 스키마는 Alembic(`db_upgrade upgrade head`)이 권위 소스.
    # create_all 을 호출하지 않아 마이그레이션과의 충돌(이미 존재/타입 불일치)을 방지한다.


def _ensure_columns() -> None:
    """기존 테이블에 신규 컬럼을 안전하게 자동 보강(idempotent). create_all은 컬럼 추가를 못 하므로 보강.
    **모델(Base.metadata)에서 자동 도출** — 새 컬럼을 모델에 추가하면 별도 등록 없이 SQLite 에 반영된다.
    (과거엔 수동 목록이라 posts.resident 처럼 누락→'no such column' 사고 발생. 자동화로 재발 차단.)
    SQLite(개발/폴백) 전용 — 운영(PostgreSQL)은 Alembic 이 스키마 권위 소스이므로 실행하지 않는다."""
    import logging
    from sqlalchemy import inspect, text
    if engine.dialect.name != "sqlite":
        return  # 안전망: 비-SQLite 에서는 raw DDL 실행 금지(Alembic 관리)
    log = logging.getLogger("db.ensure_columns")
    try:
        from app import models  # noqa: F401  (모델 등록 보장)
        insp = inspect(engine)
        for table_name, table in Base.metadata.tables.items():
            if not insp.has_table(table_name):
                continue  # 신규 테이블은 create_all 이 통째로 생성
            existing = {c["name"] for c in insp.get_columns(table_name)}
            for col in table.columns:
                if col.name in existing:
                    continue
                try:
                    ddl_type = col.type.compile(dialect=engine.dialect)
                except Exception:
                    ddl_type = "TEXT"
                try:
                    with engine.begin() as conn:
                        # SQLite ADD COLUMN 은 NOT NULL(기본값 없음) 불가 → 항상 nullable 로 추가
                        conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {ddl_type}'))
                        # boolean/integer 신규 컬럼은 기존 행이 NULL → 필터 안전 위해 0 백필
                        tn = str(col.type).upper()
                        if any(k in tn for k in ("BOOL", "INT")):
                            conn.execute(text(f'UPDATE "{table_name}" SET "{col.name}" = 0 '
                                              f'WHERE "{col.name}" IS NULL'))
                    log.info("스키마 자동 보강: %s.%s (%s) 추가", table_name, col.name, ddl_type)
                except Exception as e:
                    log.warning("컬럼 보강 실패(무시): %s.%s — %s", table_name, col.name, e)
    except Exception as e:
        log.warning("_ensure_columns 스킵: %s", e)
