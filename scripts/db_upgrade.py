"""DB 마이그레이션 실행기 — 운영/배포용 단일 명령.

왜 필요한가:
  - 운영/스테이징은 create_all 이 아니라 Alembic 으로 스키마를 관리해야 한다(드리프트/롤백 안전).
  - alembic.ini 에 URL 을 적지 않고, 앱 설정(effective_database_url)을 그대로 사용한다
    → .env 한 곳에서 DB 를 관리(웹/배치/마이그레이션 일관).

사용법:
  python -m scripts.db_upgrade            # = upgrade head (스키마를 최신으로)
  python -m scripts.db_upgrade upgrade head
  python -m scripts.db_upgrade current    # 현재 리비전 확인
  python -m scripts.db_upgrade history    # 마이그레이션 이력
  python -m scripts.db_upgrade stamp head # (기존 create_all DB 를 Alembic 이력에 편입)
  python -m scripts.db_upgrade downgrade -1

배포 순서(권장): (1) 이미지 빌드 → (2) `db_upgrade upgrade head` → (3) 앱 롤아웃.
무중단을 위해 마이그레이션은 가능하면 '추가형(additive)'으로 작성한다(컬럼 추가 후 코드 배포).
"""
from __future__ import annotations
import sys
from pathlib import Path

from alembic.config import Config
from alembic import command



def _cfg() -> Config:
    root = Path(__file__).resolve().parents[1]
    # alembic.ini 를 직접 읽지 않는다(Windows cp949 로케일에서 비ASCII ini 디코딩 오류 방지).
    # script_location 만 코드로 주입하고, DB URL 은 env.py 가 설정에서 직접 사용한다.
    cfg = Config()
    cfg.set_main_option("script_location", str(root / "migrations"))
    # sqlalchemy.url 은 여기서 넣지 않는다. migrations/env.py 가 설정에서 직접 읽어
    # create_engine 으로 사용한다(ConfigParser 의 % 보간/인코딩 이슈 회피).
    return cfg


def main(argv: list[str]) -> int:
    cfg = _cfg()
    args = argv or ["upgrade", "head"]
    action = args[0]
    rest = args[1:]
    if action == "upgrade":
        command.upgrade(cfg, rest[0] if rest else "head")
    elif action == "downgrade":
        command.downgrade(cfg, rest[0] if rest else "-1")
    elif action == "stamp":
        command.stamp(cfg, rest[0] if rest else "head")
    elif action == "current":
        command.current(cfg, verbose=True)
    elif action == "history":
        command.history(cfg, verbose=True)
    else:
        print(f"알 수 없는 명령: {action}")
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
