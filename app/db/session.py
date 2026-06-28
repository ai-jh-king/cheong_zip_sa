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
    """기존 테이블에 신규 컬럼을 안전하게 추가(idempotent). create_all은 컬럼 추가를 못 하므로 보강.
    SQLite(개발) 전용 — 운영(PostgreSQL)은 Alembic 이 스키마를 관리하므로 호출되지 않는다.
    (raw DDL 문자열은 SQLite 기준이라 PG 에서는 절대 실행하지 않는다)"""
    from sqlalchemy import inspect, text
    if engine.dialect.name != "sqlite":
        return  # 안전망: 비-SQLite 에서는 raw DDL 실행 금지
    wanted = {
        "posts": [("images", "JSON"), ("complex_name", "VARCHAR(120)"),
                  ("property_type", "VARCHAR(20)")],
        "comments": [("parent_id", "INTEGER")],
        "notifications": [("complex_name", "VARCHAR(120)"), ("lawd_cd", "VARCHAR(5)"),
                          ("property_type", "VARCHAR(20)")],
        "complexes": [("kapt_code", "VARCHAR(20)"), ("dong_count", "INTEGER"),
                      ("heating", "VARCHAR(40)"), ("total_area", "FLOAT"),
                      ("builder", "VARCHAR(120)"), ("approval_date", "VARCHAR(20)"),
                      ("parking", "INTEGER"), ("price_official", "INTEGER"),
                      ("price_basis_date", "VARCHAR(20)"), ("meta_source", "VARCHAR(40)"),
                      ("enriched_at", "DATETIME")],
        "transactions": [("identity_key", "VARCHAR(220)"), ("is_canceled", "BOOLEAN"),
                         ("canceled_date", "DATE"), ("corrected_at", "DATETIME")],
    }
    try:
        insp = inspect(engine)
        for table, cols in wanted.items():
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols:
                if name in existing:
                    continue
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                        # 신규 boolean 컬럼은 기존 행이 NULL → 0(미해제)로 백필(필터 안전)
                        if table == "transactions" and name == "is_canceled":
                            conn.execute(text("UPDATE transactions SET is_canceled = 0 "
                                              "WHERE is_canceled IS NULL"))
                except Exception:
                    pass
    except Exception:
        pass
