"""Alembic 환경. DB URL 은 app 설정(effective_database_url)에서 '직접' 가져온다.
ConfigParser(보간 %, 로케일 인코딩) 경로를 거치지 않아, 비밀번호에 % 나 @(=%40) 같은
문자가 있어도 안전하다. target_metadata 는 app.models 의 Base.metadata(autogenerate 지원).
로컬은 SQLite, 운영은 PostgreSQL — 같은 모델로 동작."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings
from app.db.session import Base
import app.models  # noqa: F401  (모든 모델 등록)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# DB URL 은 ConfigParser 를 거치지 않고 설정에서 직접 사용(%/@ 인코딩 안전).
DB_URL = get_settings().effective_database_url


def run_migrations_offline() -> None:
    context.configure(url=DB_URL, target_metadata=target_metadata,
                      literal_binds=True, compare_type=True,
                      render_as_batch=DB_URL.startswith("sqlite"))
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(DB_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(connection=connection, target_metadata=target_metadata,
                          compare_type=True, render_as_batch=is_sqlite)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
