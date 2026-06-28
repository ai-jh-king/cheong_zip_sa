"""관심 등록(즐겨찾기) API.
- 비로그인: 익명 device_id 기준. 로그인: 계정에 연결된 모든 device를 합쳐 cross-device.
- 개인정보 없음.
"""
from fastapi import APIRouter, Depends, Query, Header
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Favorite
from app.api.auth import owner_device_ids

router = APIRouter(prefix="/favorites", tags=["favorites"])


class FavoriteIn(BaseModel):
    device_id: str
    target_type: str = "complex"
    target_id: str
    name: str | None = None
    meta: dict | None = None


def _row(f: Favorite) -> dict:
    return {"id": f.id, "target_type": f.target_type, "target_id": f.target_id,
            "name": f.name, "meta": f.meta or {}}


@router.get("")
def list_favorites(db: Session = Depends(get_db), device_id: str = Query(...),
                   authorization: str | None = Header(None)):
    ids = owner_device_ids(db, device_id, authorization)
    rows = db.scalars(select(Favorite).where(Favorite.device_id.in_(ids))
                      .order_by(Favorite.created_at.desc())).all()
    # 여러 device 합산 시 동일 대상 중복 제거(최신 우선)
    seen, items = set(), []
    for f in rows:
        key = (f.target_type, f.target_id)
        if key in seen:
            continue
        seen.add(key)
        items.append(_row(f))
    return {"items": items}


@router.post("")
def add_favorite(body: FavoriteIn, db: Session = Depends(get_db),
                 authorization: str | None = Header(None)):
    ids = owner_device_ids(db, body.device_id, authorization)
    exists = db.scalar(select(Favorite).where(
        Favorite.device_id.in_(ids),
        Favorite.target_type == body.target_type,
        Favorite.target_id == body.target_id))
    if exists:
        return {"ok": True, "item": _row(exists), "duplicated": True}
    f = Favorite(device_id=body.device_id, target_type=body.target_type,
                 target_id=body.target_id, name=body.name, meta=body.meta)
    db.add(f)
    db.commit()
    db.refresh(f)
    return {"ok": True, "item": _row(f)}


@router.delete("")
def remove_favorite(db: Session = Depends(get_db), device_id: str = Query(...),
                    target_type: str = Query("complex"), target_id: str = Query(...),
                    authorization: str | None = Header(None)):
    ids = owner_device_ids(db, device_id, authorization)
    db.execute(delete(Favorite).where(
        Favorite.device_id.in_(ids),
        Favorite.target_type == target_type,
        Favorite.target_id == target_id))
    db.commit()
    return {"ok": True}
