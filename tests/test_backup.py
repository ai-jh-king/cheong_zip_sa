"""백업 스크립트 단위 테스트 — URL 파싱 / 보관주기 정리(외부 의존성 없음)."""
import pathlib
import tempfile

from scripts.backup import parse_db_url, prune, PREFIX


def test_parse_postgres_url():
    p = parse_db_url("postgresql+psycopg2://u:p%40ss@db.host:6543/cheongju")
    assert p["is_sqlite"] is False
    assert p["user"] == "u" and p["password"] == "p@ss"
    assert p["host"] == "db.host" and p["port"] == 6543 and p["dbname"] == "cheongju"


def test_parse_postgres_defaults():
    p = parse_db_url("postgresql://app@localhost/db")
    assert p["port"] == 5432 and p["host"] == "localhost" and p["password"] == ""


def test_parse_sqlite_url():
    p = parse_db_url("sqlite:///./cheongju_local.db")
    assert p["is_sqlite"] is True and p["path"] == "./cheongju_local.db"


def test_prune_keeps_latest():
    d = pathlib.Path(tempfile.mkdtemp())
    for i in range(5):
        (d / f"{PREFIX}2026010{i}_000000.dump").write_text("x")
    removed = prune(d, 2)
    left = sorted(p.name for p in d.glob(PREFIX + "*"))
    assert removed == 3 and len(left) == 2
    assert left[-1].endswith("20260104_000000.dump")  # 최신 보존


def test_prune_noop_when_under_keep():
    d = pathlib.Path(tempfile.mkdtemp())
    (d / f"{PREFIX}20260101_000000.dump").write_text("x")
    assert prune(d, 14) == 0
