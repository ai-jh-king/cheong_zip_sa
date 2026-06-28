"""매물 문의(리드) API — 첫 매출(B2B) 기반.

원칙(왜곡 없음·개인정보 9.A 준용):
- 문의 연락처(contact)는 매물 소유자(중개사) 응대를 위해 저장한다. **소유자만 열람**.
- 작성자 **동의(consent) 없이는 생성 거부**. 마케팅·제3자 제공 금지.
- 본 서비스는 게시판이며 중개행위가 아니다. '문의=계약 보장' 아님(프런트 고지).
- 과금 게이트는 현재 OFF(무료도 전체 열람). 추후 plan 기반 게이트는 entitlement로 연결.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import select, or_, func, case
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Listing, Inquiry
from app.api.auth import account_from_auth
from app.core.config import get_settings
from app.services.entitlement import is_premium

router = APIRouter(prefix="/inquiries", tags=["inquiries"])

VALID_STATUS = {"new", "read", "contacted", "closed"}


class InquiryIn(BaseModel):
    listing_id: int
    device_id: str | None = None          # 문의자(익명)
    name: str | None = Field(None, max_length=40)
    contact: str = Field(min_length=2, max_length=120)
    message: str = Field(min_length=1, max_length=1000)
    consent: bool = False


class StatusIn(BaseModel):
    status: str


def _row(x: Inquiry, listing: Listing | None = None, mask: bool = False) -> dict:
    d = {
        "id": x.id, "listing_id": x.listing_id,
        "name": x.name,
        "contact": (None if mask else x.contact),
        "locked": bool(mask),
        "message": x.message,
        "status": x.status, "created_at": x.created_at.isoformat() if x.created_at else None,
    }
    if listing is not None:
        d["listing_title"] = listing.title
        d["deal_type"] = listing.deal_type
        d["listing_status"] = listing.status
    return d


@router.post("")
def create_inquiry(body: InquiryIn, db: Session = Depends(get_db),
                   authorization: str | None = Header(None)):
    """매물에 문의 남기기(누구나). 동의 필수. 소유자 정보 비정규화 저장."""
    if not body.consent:
        raise HTTPException(status_code=400, detail="연락처가 등록자(중개사)에게 전달되는 것에 동의해야 문의할 수 있어요.")
    x = db.get(Listing, body.listing_id)
    if not x or x.status == "hidden":
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다.")
    inq = Inquiry(
        listing_id=x.id,
        owner_account_id=x.account_id,
        owner_device_id=x.device_id,
        inquirer_device_id=body.device_id,
        name=(body.name or "").strip() or None,
        contact=body.contact.strip(),
        message=body.message.strip(),
        consent=True,
        status="new",
    )
    db.add(inq)
    db.commit()
    return {"ok": True, "id": inq.id}


@router.get("")
def list_inquiries(db: Session = Depends(get_db),
                   device_id: str = Query("", description="익명 소유자 식별"),
                   listing_id: int | None = Query(None, description="특정 매물만"),
                   authorization: str | None = Header(None)):
    """소유자가 받은 문의(리드) 목록. 소유자만(계정 또는 device). 연락처 포함은 소유자 한정."""
    acc = account_from_auth(db, authorization)
    conds = []
    if acc:
        conds.append(Inquiry.owner_account_id == acc.id)
    if device_id:
        conds.append(Inquiry.owner_device_id == device_id)
    if not conds:
        raise HTTPException(status_code=401, detail="로그인 또는 device_id가 필요합니다.")
    q = select(Inquiry).where(or_(*conds))
    if listing_id is not None:
        q = q.where(Inquiry.listing_id == listing_id)
    q = q.order_by(Inquiry.created_at.desc())
    rows = list(db.execute(q).scalars().all())
    # 매물 제목 매핑(N+1 방지: 한 번에 조회)
    lids = {r.listing_id for r in rows}
    lmap = {}
    if lids:
        for l in db.execute(select(Listing).where(Listing.id.in_(lids))).scalars().all():
            lmap[l.id] = l
    # 연락처 마스킹: 결제/수익화 플래그 ON + 비프리미엄일 때만(기본 OFF=전체 노출, 현재와 동일).
    st = get_settings()
    gating = st.feature_billing or st.feature_monetization
    mask = bool(gating and not is_premium(acc, db))
    items = [_row(r, lmap.get(r.listing_id), mask) for r in rows]
    new_cnt = sum(1 for r in rows if r.status == "new")
    return {"items": items, "total": len(items), "new": new_cnt, "locked": mask}


@router.get("/summary")
def inquiry_summary(db: Session = Depends(get_db),
                    device_id: str = Query(""),
                    authorization: str | None = Header(None)):
    """매물별 문의 건수 집계(소유자) — 대시보드 카드용."""
    acc = account_from_auth(db, authorization)
    conds = []
    if acc:
        conds.append(Inquiry.owner_account_id == acc.id)
    if device_id:
        conds.append(Inquiry.owner_device_id == device_id)
    if not conds:
        raise HTTPException(status_code=401, detail="로그인 또는 device_id가 필요합니다.")
    rows = db.execute(
        select(Inquiry.listing_id, func.count().label("c"),
               func.sum(case((Inquiry.status == "new", 1), else_=0)).label("n"))
        .where(or_(*conds)).group_by(Inquiry.listing_id)
    ).all()
    by_listing = {r[0]: {"total": int(r[1] or 0), "new": int(r[2] or 0)} for r in rows}
    total = sum(v["total"] for v in by_listing.values())
    new = sum(v["new"] for v in by_listing.values())
    return {"by_listing": by_listing, "total": total, "new": new}


@router.post("/{inquiry_id}/status")
def set_inquiry_status(inquiry_id: int, body: StatusIn, db: Session = Depends(get_db),
                       device_id: str = Query(""),
                       authorization: str | None = Header(None)):
    """소유자만 문의 상태 변경(new/read/contacted/closed)."""
    inq = db.get(Inquiry, inquiry_id)
    if not inq:
        raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다.")
    acc = account_from_auth(db, authorization)
    is_owner = (acc and inq.owner_account_id and inq.owner_account_id == acc.id) \
        or (device_id and inq.owner_device_id and inq.owner_device_id == device_id)
    if not is_owner:
        raise HTTPException(status_code=403, detail="매물 등록자만 변경할 수 있습니다.")
    if body.status not in VALID_STATUS:
        raise HTTPException(status_code=400, detail="status는 new/read/contacted/closed 중 하나여야 합니다.")
    inq.status = body.status
    db.commit()
    return {"ok": True, "status": inq.status}
