"""DB 복구 — 백업 파일에서 복원(PostgreSQL pg_restore / SQLite 해제).

⚠️ 복구는 현재 데이터를 덮어씁니다. 반드시 확인 후 실행하세요.

사용:
  python -m scripts.restore --list                 # 복구 가능한 백업 목록
  python -m scripts.restore <파일명> --yes         # 해당 백업으로 복원

PostgreSQL: pg_restore --clean --if-exists 로 복원(기존 객체 정리 후 적재).
SQLite: 현재 DB 파일을 .bak 로 옮기고 백업(.gz)을 해제해 교체.
"""
from __future__ import annotations
import gzip
import os
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.backup import parse_db_url, list_backups, PREFIX  # 재사용


def _restore_sqlite(params: dict, src: Path) -> None:
    dst = Path(params["path"])
    if dst.exists():
        shutil.move(str(dst), str(dst) + ".bak")
    with gzip.open(src, "rb") as fi, open(dst, "wb") as fo:
        shutil.copyfileobj(fi, fo)


def _restore_postgres(params: dict, src: Path) -> None:
    env = dict(os.environ)
    if params["password"]:
        env["PGPASSWORD"] = params["password"]
    cmd = ["pg_restore", "--clean", "--if-exists", "--no-owner",
           "-h", str(params["host"]), "-p", str(params["port"]),
           "-U", params["user"], "-d", params["dbname"], str(src)]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=3600)
    # pg_restore 는 일부 경고에도 rc!=0 가능 → stderr 출력하되 치명 오류만 예외
    if proc.returncode != 0 and "error" in (proc.stderr or "").lower():
        raise RuntimeError(f"pg_restore 실패(rc={proc.returncode}): {proc.stderr.strip()[:400]}")


def main() -> int:
    import logging
    from app.core.config import get_settings
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s [restore]: %(message)s")
    log = logging.getLogger("restore")
    args = sys.argv[1:]
    if "--list" in args or not args:
        for b in list_backups():
            log.info("%s  (%d bytes)", b["file"], b["bytes"])
        if not args:
            log.info("복원하려면: python -m scripts.restore <파일명> --yes")
        return 0
    fname = next((a for a in args if a.startswith(PREFIX)), None)
    if not fname:
        log.error("복원할 백업 파일명을 지정하세요(예: %s20260621_010000.dump).", PREFIX)
        return 1
    if "--yes" not in args:
        log.error("덮어쓰기 확인이 필요합니다. 명령 끝에 --yes 를 붙이세요.")
        return 1
    s = get_settings()
    src = Path(s.backup_dir) / fname
    if not src.exists():
        log.error("백업 파일이 없습니다: %s", src)
        return 1
    params = parse_db_url(s.effective_database_url)
    log.info("복원 시작: %s → %s", src.name, "sqlite" if params["is_sqlite"] else "postgres")
    if params["is_sqlite"]:
        _restore_sqlite(params, src)
    else:
        _restore_postgres(params, src)
    log.info("복원 완료. 앱을 재기동하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
