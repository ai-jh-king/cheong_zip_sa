"""DB 백업 — PostgreSQL(pg_dump) / SQLite(파일 복사) + 보관주기 정리.

사용:
  python -m scripts.backup            # 1회 백업 + 오래된 백업 정리
  python -m scripts.backup --list     # 백업 목록만 출력

동작:
- effective_database_url 을 파싱해 PostgreSQL 이면 `pg_dump -Fc`(압축·pg_restore용),
  SQLite 면 파일을 gzip 복사.
- 파일명: cheongju_YYYYmmdd_HHMMSS.(dump|sqlite.gz) — backup_dir 에 저장.
- backup_keep 개수만 남기고 오래된 백업 삭제.
- monitoring.record_job("backup") 으로 성공/실패 기록 + 실패 시 경보.

복구는 scripts/restore.py 또는 OPERATIONS.md 참조.
주의: pg_dump 가 PATH 에 있어야 함(PostgreSQL 클라이언트 설치).
"""
from __future__ import annotations
import gzip
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, unquote

PREFIX = "cheongju_"


def parse_db_url(url: str) -> dict:
    """DATABASE_URL 파싱(테스트 가능, 외부 의존성 없음)."""
    u = urlsplit(url)
    scheme = (u.scheme or "").split("+")[0]
    if scheme.startswith("sqlite"):
        path = u.path or ""
        # sqlite:///rel.db → '/rel.db' → 'rel.db' ; sqlite:////abs.db → '//abs.db' → '/abs.db'
        if path.startswith("/"):
            path = path[1:]
        return {"driver": scheme, "is_sqlite": True, "path": path}
    return {
        "driver": scheme, "is_sqlite": False,
        "user": unquote(u.username or ""), "password": unquote(u.password or ""),
        "host": u.hostname or "localhost", "port": u.port or 5432,
        "dbname": (u.path or "/").lstrip("/"),
    }


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def prune(backup_dir: Path, keep: int) -> int:
    """prefix 백업을 최신 keep개만 남기고 삭제. 반환=삭제 수."""
    files = sorted([p for p in backup_dir.glob(PREFIX + "*") if p.is_file()],
                   key=lambda p: p.name)
    removed = 0
    if keep > 0 and len(files) > keep:
        for p in files[:-keep]:
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
    return removed


def _backup_sqlite(params: dict, out_dir: Path) -> Path:
    src = Path(params["path"])
    if not src.exists():
        raise FileNotFoundError(f"SQLite 파일이 없습니다: {src}")
    out = out_dir / f"{PREFIX}{_stamp()}.sqlite.gz"
    with open(src, "rb") as fi, gzip.open(out, "wb") as fo:
        shutil.copyfileobj(fi, fo)
    return out


def _backup_postgres(params: dict, out_dir: Path) -> Path:
    out = out_dir / f"{PREFIX}{_stamp()}.dump"
    env = dict(os.environ)
    if params["password"]:
        env["PGPASSWORD"] = params["password"]
    cmd = ["pg_dump", "-h", str(params["host"]), "-p", str(params["port"]),
           "-U", params["user"], "-d", params["dbname"], "-Fc", "-f", str(out)]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0:
        raise RuntimeError(f"pg_dump 실패(rc={proc.returncode}): {proc.stderr.strip()[:300]}")
    return out


def run_backup() -> dict:
    """백업 1회 수행 + 정리. 반환 통계(JobRun 기록용)."""
    from app.core.config import get_settings
    s = get_settings()
    params = parse_db_url(s.effective_database_url)
    out_dir = Path(s.backup_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = _backup_sqlite(params, out_dir) if params["is_sqlite"] else _backup_postgres(params, out_dir)
    size = out.stat().st_size if out.exists() else 0
    removed = prune(out_dir, s.backup_keep)
    return {"file": out.name, "bytes": size, "engine": "sqlite" if params["is_sqlite"] else "postgres",
            "pruned": removed, "kept": s.backup_keep}


def list_backups() -> list[dict]:
    from app.core.config import get_settings
    out_dir = Path(get_settings().backup_dir)
    if not out_dir.exists():
        return []
    return [{"file": p.name, "bytes": p.stat().st_size,
             "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat()}
            for p in sorted(out_dir.glob(PREFIX + "*"))]


def main() -> int:
    import logging
    from app.core.config import get_settings
    logging.basicConfig(level=get_settings().log_level,
                        format="%(asctime)s %(levelname)s [backup]: %(message)s")
    log = logging.getLogger("backup")
    if "--list" in sys.argv:
        for b in list_backups():
            log.info("%s  (%d bytes)", b["file"], b["bytes"])
        return 0
    from app.db.session import init_db, SessionLocal
    from app.services.monitoring import record_job
    init_db()
    with SessionLocal() as db:
        try:
            res = record_job(db, "backup", run_backup)
            log.info("백업 완료: %s", res)
            return 0
        except Exception as e:  # noqa
            log.error("백업 실패: %s", e)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
