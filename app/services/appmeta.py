"""app_meta(키-값) 영속 헬퍼 — 알림 커서·수집 워터마크 등 운영 상태 저장/조회.

cache.py 의 인메모리 캐시와 달리 '재시작에도 남아야 하는' 작은 상태를 DB 에 둔다.
"""
from __future__ import annotations
import json

from sqlalchemy.orm import Session

from app.models import AppMeta


def get(db: Session, key: str, default: str | None = None) -> str | None:
    row = db.get(AppMeta, key)
    return row.value if row else default


def set(db: Session, key: str, value, commit: bool = True) -> None:  # noqa: A001
    row = db.get(AppMeta, key)
    if row:
        row.value = str(value)
    else:
        db.add(AppMeta(key=key, value=str(value)))
    if commit:
        db.commit()


def get_int(db: Session, key: str, default: int = 0) -> int:
    try:
        return int(get(db, key))
    except (TypeError, ValueError):
        return default


def get_json(db: Session, key: str, default=None):
    raw = get(db, key)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def set_json(db: Session, key: str, obj, commit: bool = True) -> None:
    set(db, key, json.dumps(obj, ensure_ascii=False), commit=commit)
