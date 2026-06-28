"""개인화 API — 비로그인은 device_id, 로그인은 계정 연결 device 전체를 union.
  - GET/PUT /me/prefs    : 표시 설정·내 동네 등(JSON)
  - GET/POST /me/recent  : 최근 본 단지(최신순, 상한 20)
  - GET/POST/DELETE /me/searches : 저장 검색
개인정보 없음(소득·신용 등 미수집).
"""
from fastapi import APIRouter, Depends, Query, Header
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import UserPref, RecentView, SavedSearch
from app.api.auth import owner_device_ids

router = APIRouter(prefix="/me", tags=["personal"])
RECENT_CAP = 20
SEARCH_CAP = 30


class PrefsIn(BaseModel):
    device_id: str
    data: dict = {}


class RecentIn(BaseModel):
    device_id: str
    target_id: str
    name: str | None = None
    meta: dict | None = None


class SavedSearchIn(BaseModel):
    device_id: str
    name: str | None = None
    filters: dict = {}


@router.get("/prefs")
def get_prefs(db: Session = Depends(get_db), device_id: str = Query(...),
              authorization: str | None = Header(None)):
    # 현재 device 우선, 없으면 계정 연결 device 중 데이터가 있는 것
    row = db.get(UserPref, device_id)
    if not (row and row.data):
        ids = owner_device_ids(db, device_id, authorization)
        row = db.scalar(select(UserPref).where(UserPref.device_id.in_(ids),
                                               UserPref.data.isnot(None)))
    return {"data": (row.data if row and row.data else {})}


@router.put("/prefs")
def put_prefs(body: PrefsIn, db: Session = Depends(get_db)):
    row = db.get(UserPref, body.device_id)
    if row:
        row.data = body.data
    else:
        db.add(UserPref(device_id=body.device_id, data=body.data))
    db.commit()
    return {"ok": True, "data": body.data}


@router.get("/recent")
def get_recent(db: Session = Depends(get_db), device_id: str = Query(...),
               limit: int = Query(10, ge=1, le=20),
               authorization: str | None = Header(None)):
    ids = owner_device_ids(db, device_id, authorization)
    rows = db.scalars(select(RecentView).where(RecentView.device_id.in_(ids))
                      .order_by(RecentView.viewed_at.desc())).all()
    seen, items = set(), []
    for r in rows:
        if r.target_id in seen:
            continue
        seen.add(r.target_id)
        items.append({"target_id": r.target_id, "name": r.name, "meta": r.meta or {}})
        if len(items) >= limit:
            break
    return {"items": items}


@router.post("/recent")
def add_recent(body: RecentIn, db: Session = Depends(get_db)):
    db.execute(delete(RecentView).where(
        RecentView.device_id == body.device_id,
        RecentView.target_id == body.target_id))
    db.add(RecentView(device_id=body.device_id, target_id=body.target_id,
                      name=body.name, meta=body.meta))
    db.commit()
    ids = db.scalars(select(RecentView.id).where(RecentView.device_id == body.device_id)
                     .order_by(RecentView.viewed_at.desc())).all()
    if len(ids) > RECENT_CAP:
        db.execute(delete(RecentView).where(RecentView.id.in_(ids[RECENT_CAP:])))
        db.commit()
    return {"ok": True}


@router.get("/searches")
def get_searches(db: Session = Depends(get_db), device_id: str = Query(...),
                 authorization: str | None = Header(None)):
    ids = owner_device_ids(db, device_id, authorization)
    rows = db.scalars(select(SavedSearch).where(SavedSearch.device_id.in_(ids))
                      .order_by(SavedSearch.created_at.desc())).all()
    return {"items": [{"id": r.id, "name": r.name, "filters": r.filters or {}}
                      for r in rows]}


@router.post("/searches")
def add_search(body: SavedSearchIn, db: Session = Depends(get_db)):
    row = SavedSearch(device_id=body.device_id, name=body.name, filters=body.filters)
    db.add(row)
    db.commit()
    db.refresh(row)
    ids = db.scalars(select(SavedSearch.id).where(SavedSearch.device_id == body.device_id)
                     .order_by(SavedSearch.created_at.desc())).all()
    if len(ids) > SEARCH_CAP:
        db.execute(delete(SavedSearch).where(SavedSearch.id.in_(ids[SEARCH_CAP:])))
        db.commit()
    return {"ok": True, "id": row.id}


@router.delete("/searches/{search_id}")
def del_search(search_id: int, db: Session = Depends(get_db), device_id: str = Query(...),
               authorization: str | None = Header(None)):
    ids = owner_device_ids(db, device_id, authorization)
    db.execute(delete(SavedSearch).where(
        SavedSearch.id == search_id, SavedSearch.device_id.in_(ids)))
    db.commit()
    return {"ok": True}
