"""집사 도감 API — 청집사가 직접 쓰는 실사용 안내서(콘텐츠 시스템).

- 공개: 시리즈 목록 / 시리즈 상세(편 목록) / 편 상세(마크다운 raw) / 조회수 증가
- 관리자: 작성/수정/삭제 (X-Admin-Token, admin.py 와 동일 타이밍세이프 검증)

원칙(왜곡 없음): 본문은 사실+근거만. 판정·투자 권유 금지(발행 검수는 운영 절차).
조회수는 원자 UPDATE(카운터 규약). 편 목록은 published 만 노출(초안 제외).
"""
from __future__ import annotations
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Guide, GuideSeries

router = APIRouter(prefix="/guides", tags=["guides"])
admin_router = APIRouter(prefix="/admin/guides", tags=["guides-admin"])   # 관리자 CRUD(스펙 경로)

IDENTITY_NOTE = "청집사는 중개·광고 수익이 없어 특정 매물을 권유하지 않습니다. 본문은 사실·근거 기반 참고용입니다."


def _require_admin(x_admin_token: str | None):
    s = get_settings()
    if not s.admin_token:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN 미설정 — 관리자 기능 비활성")
    if not (x_admin_token and hmac.compare_digest(x_admin_token, s.admin_token)):
        raise HTTPException(status_code=401, detail="관리자 토큰이 올바르지 않습니다.")


def _series_row(s: GuideSeries, count: int | None = None) -> dict:
    d = {"key": s.key, "name": s.name, "description": s.description,
         "cover_emoji": s.cover_emoji, "sort_order": s.sort_order}
    if count is not None:
        d["guide_count"] = count
    return d


def _guide_row(g: Guide, with_body: bool = False) -> dict:
    d = {"id": g.id, "series_key": g.series_key, "title": g.title,
         "cover_emoji": g.cover_emoji, "sort_order": g.sort_order,
         "view_count": g.view_count or 0,
         "published_at": g.published_at.isoformat() if g.published_at else None,
         "updated_at": g.updated_at.isoformat() if g.updated_at else None}
    if with_body:
        d["body_md"] = g.body_md
    return d


@router.get("/series")
def list_series(db: Session = Depends(get_db)):
    """활성 시리즈 목록(+발행 편수). 도감 첫 화면."""
    rows = db.scalars(select(GuideSeries).where(GuideSeries.is_active.is_(True))
                      .order_by(GuideSeries.sort_order, GuideSeries.key)).all()
    counts = dict(db.execute(
        select(Guide.series_key, func.count()).where(Guide.is_published.is_(True))
        .group_by(Guide.series_key)).all())
    return {"series": [_series_row(s, counts.get(s.key, 0)) for s in rows],
            "notice": IDENTITY_NOTE}


@router.get("/series/{key}")
def series_detail(key: str, db: Session = Depends(get_db)):
    """시리즈 상세 + 발행된 편 목록(본문 제외 — 목록 가볍게)."""
    s = db.get(GuideSeries, key)
    if not s or not s.is_active:
        raise HTTPException(status_code=404, detail="시리즈를 찾을 수 없습니다.")
    guides = db.scalars(select(Guide)
                        .where(Guide.series_key == key, Guide.is_published.is_(True))
                        .order_by(Guide.sort_order, Guide.id)).all()
    return {"series": _series_row(s), "guides": [_guide_row(g) for g in guides],
            "notice": IDENTITY_NOTE}


@router.get("/{gid}")
def guide_detail(gid: int, db: Session = Depends(get_db)):
    """편 상세(마크다운 raw + 이전/다음 편 네비게이션)."""
    g = db.get(Guide, gid)
    if not g or not g.is_published:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다.")
    sibs = db.scalars(select(Guide)
                      .where(Guide.series_key == g.series_key, Guide.is_published.is_(True))
                      .order_by(Guide.sort_order, Guide.id)).all()
    ids = [x.id for x in sibs]
    i = ids.index(g.id) if g.id in ids else -1
    prev_g = sibs[i - 1] if i > 0 else None
    next_g = sibs[i + 1] if 0 <= i < len(sibs) - 1 else None
    s = db.get(GuideSeries, g.series_key)
    return {"guide": _guide_row(g, with_body=True),
            "series": _series_row(s) if s else None,
            "prev": {"id": prev_g.id, "title": prev_g.title} if prev_g else None,
            "next": {"id": next_g.id, "title": next_g.title} if next_g else None,
            "notice": IDENTITY_NOTE}


@router.post("/{gid}/view")
def add_view(gid: int, db: Session = Depends(get_db)):
    """조회수 증가 — 원자 UPDATE(카운터 규약: read-modify-write 금지)."""
    db.execute(update(Guide).where(Guide.id == gid)
               .values(view_count=func.coalesce(Guide.view_count, 0) + 1))
    db.commit()
    return {"ok": True}


# ---------------- 관리자(작성·수정·삭제) ----------------

class GuideBody(BaseModel):
    series_key: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=2, max_length=160)
    body_md: str = Field(min_length=10)
    cover_emoji: str | None = Field(default=None, max_length=8)
    sort_order: int = 0
    is_published: bool = True


@admin_router.post("")
def create_guide(b: GuideBody, db: Session = Depends(get_db),
                 x_admin_token: str | None = Header(None)):
    _require_admin(x_admin_token)
    if not db.get(GuideSeries, b.series_key):
        raise HTTPException(status_code=422, detail=f"시리즈 '{b.series_key}' 가 없습니다. 먼저 시리즈를 만드세요.")
    g = Guide(series_key=b.series_key, title=b.title.strip(), body_md=b.body_md,
              cover_emoji=b.cover_emoji, sort_order=b.sort_order, is_published=b.is_published)
    db.add(g)
    db.commit()
    return {"ok": True, "guide": _guide_row(g)}


@admin_router.put("/{gid}")
def update_guide(gid: int, b: GuideBody, db: Session = Depends(get_db),
                 x_admin_token: str | None = Header(None)):
    _require_admin(x_admin_token)
    g = db.get(Guide, gid)
    if not g:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다.")
    g.series_key, g.title, g.body_md = b.series_key, b.title.strip(), b.body_md
    g.cover_emoji, g.sort_order, g.is_published = b.cover_emoji, b.sort_order, b.is_published
    db.commit()
    return {"ok": True, "guide": _guide_row(g)}


@admin_router.delete("/{gid}")
def delete_guide(gid: int, db: Session = Depends(get_db),
                 x_admin_token: str | None = Header(None)):
    _require_admin(x_admin_token)
    g = db.get(Guide, gid)
    if not g:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다.")
    db.delete(g)
    db.commit()
    return {"ok": True}
