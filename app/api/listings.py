"""등록 매물(UGC) API — 사용자/중개업자가 올린 매물.

원칙(왜곡 방지):
- 등록 매물은 '실거래(Transaction)'와 분리한다. 응답에 source="listing"을 명시해
  프런트가 실거래와 절대 섞지 않도록 한다.
- 「중개대상물의 표시·광고 명시사항 세부기준」(국토부 고시)의 명시 항목을 받는다.
  poster_role=="agent"(개업공인중개사)면 사무소 명시사항을 필수로 요구한다.
- 본 서비스는 '게시판' 기능이며 중개행위가 아니다. 허위매물·연락처 노출 주의 고지는 프런트에서.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Header
from pydantic import BaseModel, Field
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Listing
from app.data.region_codes import CHEONGJU_DISTRICTS
from app.core.config import get_settings
from app.services import storage
from app.api.auth import account_from_auth

router = APIRouter(prefix="/listings", tags=["listings"])

VALID_CODES = {d.code: d.name for d in CHEONGJU_DISTRICTS}
DEAL_TYPES = {"trade", "jeonse", "wolse"}
PROP_TYPES = {"apartment", "officetel", "rowhouse", "detached", "oneroom"}
MAX_PHOTOS = 12
MAX_PHOTO_LEN = 3_500_000   # 데이터URL 1장 최대 길이(대략 2.5MB 이미지)


def _gu_name(code: str) -> str:
    return VALID_CODES.get((code or "")[:5], "청주시")


class ListingIn(BaseModel):
    device_id: str | None = None
    poster_role: str = "user"          # user | agent
    title: str = Field(min_length=1, max_length=120)
    deal_type: str
    property_type: str
    lawd_cd: str
    dong_name: str | None = None
    complex_name: str | None = None
    address_detail: str | None = None
    exclusive_area: float | None = None
    supply_area: float | None = None
    floor: int | None = None
    total_floor: int | None = None
    rooms: int | None = None
    baths: int | None = None
    direction: str | None = None
    price: int | None = None
    deposit: int | None = None
    monthly_rent: int | None = None
    maintenance_fee: int | None = None
    maintenance_items: str | None = None
    move_in_date: str | None = None
    approval_date: str | None = None
    options: str | None = None
    description: str | None = None
    photos: list[str] | None = None
    agent_office: str | None = None
    agent_name: str | None = None
    agent_reg_no: str | None = None
    agent_phone: str | None = None
    agent_address: str | None = None


def _validate(b: ListingIn):
    errs = []
    if b.deal_type not in DEAL_TYPES:
        errs.append("거래형태(deal_type)가 올바르지 않습니다.")
    if b.property_type not in PROP_TYPES:
        errs.append("매물 종류(property_type)가 올바르지 않습니다.")
    if b.lawd_cd not in VALID_CODES:
        errs.append("지역코드(lawd_cd)가 청주 4개 구에 속하지 않습니다.")
    # 가격(거래형태별 필수)
    if b.deal_type == "trade" and not b.price:
        errs.append("매매가를 입력하세요.")
    if b.deal_type == "jeonse" and not b.price:
        errs.append("전세 보증금을 입력하세요.")
    if b.deal_type == "wolse" and (b.deposit is None or not b.monthly_rent):
        errs.append("월세는 보증금과 월세액을 입력하세요.")
    # 명시사항: 해당층/총층, 연락처
    if not b.agent_phone:
        errs.append("연락처(전화)는 필수입니다.")
    # 개업공인중개사 광고는 사무소 명시사항 필수
    if b.poster_role == "agent":
        for f, lab in [("agent_office", "중개사무소 명칭"), ("agent_name", "개업공인중개사 성명"),
                       ("agent_reg_no", "등록번호"), ("agent_address", "사무소 소재지")]:
            if not getattr(b, f):
                errs.append(f"중개업자 등록 시 '{lab}'은(는) 필수입니다.")
    # 사진 제한 — 부하 감사 H3: base64 데이터URL을 DB에 저장하면 목록 1회 조회가 수백MB
    # (50건×3.5MB) → 512MB OOM 벡터. 업로드(/listings/upload)가 URL을 돌려주므로 URL만 허용.
    if b.photos:
        if len(b.photos) > MAX_PHOTOS:
            errs.append(f"사진은 최대 {MAX_PHOTOS}장까지 가능합니다.")
        if any(len(p or "") > MAX_PHOTO_LEN for p in b.photos):
            errs.append("사진 1장 용량이 너무 큽니다(약 2.5MB 이하 권장).")
        for p in b.photos:
            u = (p or "").strip()
            if not (u.startswith("http://") or u.startswith("https://") or u.startswith("/uploads/")):
                errs.append("사진은 '사진 추가' 업로드를 통해서만 등록할 수 있습니다(외부 데이터 불가).")
                break
    if errs:
        raise HTTPException(status_code=422, detail=errs)


def _row_full(x: Listing) -> dict:
    return {
        "id": x.id, "source": "listing", "poster_role": x.poster_role,
        "title": x.title, "deal_type": x.deal_type, "property_type": x.property_type,
        "lawd_cd": x.lawd_cd, "gu": _gu_name(x.lawd_cd), "dong": x.dong_name,
        "complex_name": x.complex_name, "address_detail": x.address_detail,
        "lat": x.lat, "lng": x.lng,
        "exclusive_area": x.exclusive_area, "supply_area": x.supply_area,
        "floor": x.floor, "total_floor": x.total_floor,
        "rooms": x.rooms, "baths": x.baths, "direction": x.direction,
        "price": x.price, "deposit": x.deposit, "monthly_rent": x.monthly_rent,
        "maintenance_fee": x.maintenance_fee, "maintenance_items": x.maintenance_items,
        "move_in_date": x.move_in_date, "approval_date": x.approval_date,
        "options": x.options, "description": x.description, "photos": x.photos or [],
        "agent_office": x.agent_office, "agent_name": x.agent_name,
        "agent_reg_no": x.agent_reg_no, "agent_phone": x.agent_phone,
        "agent_address": x.agent_address,
        "status": x.status, "is_sample": x.is_sample,
        "is_sponsored": bool(getattr(x, "is_sponsored", False)), "priority": getattr(x, "priority", 0),
        "views": getattr(x, "views", 0) or 0,
        "created_at": x.created_at.isoformat() if x.created_at else None,
    }


def _row_light(x: Listing) -> dict:
    """목록용(사진은 대표 1장만 → 페이로드 절감)."""
    d = _row_full(x)
    d["photos"] = (x.photos or [])[:1]
    d.pop("description", None)
    # 연락처·상세주소는 목록에서 숨김 → 순번 ID 대량 스크래핑으로 PII 수집 방지(상세 조회에서만 노출).
    d.pop("agent_phone", None)
    d.pop("agent_address", None)
    return d


@router.get("")
def list_listings(db: Session = Depends(get_db),
                  gu: str | None = Query(None, description="법정동 5자리 코드"),
                  deal_type: str | None = Query(None),
                  property_type: str | None = Query(None),
                  device_id: str | None = Query(None, description="익명 내 매물 필터"),
                  mine: bool = Query(False, description="로그인 시 내 계정 매물만"),
                  manage: bool = Query(False, description="소유자 관리목록(전체 상태 노출). mine/device와 함께"),
                  limit: int = Query(50, le=200),
                  offset: int = Query(0, ge=0, description="페이지네이션 오프셋(0=처음)"),
                  authorization: str | None = Header(None)):
    q = select(Listing)
    acc = account_from_auth(db, authorization)
    mine_scope = bool((mine and acc) or device_id)
    if mine and acc:
        q = q.where(Listing.account_id == acc.id)
    elif device_id:
        q = q.where(Listing.device_id == device_id)
    # 공개·일반 내매물은 활성만. 소유자 관리(manage=1)일 때만 전체 상태(거래완료·숨김 포함) 노출.
    if not (mine_scope and manage):
        q = q.where(Listing.status == "active")
    if gu:
        q = q.where(Listing.lawd_cd == gu)
    if deal_type:
        q = q.where(Listing.deal_type == deal_type)
    if property_type:
        q = q.where(Listing.property_type == property_type)
    # 광고/제휴 노출: feature_ads ON일 때만 후원·우선순위 우선 정렬. OFF면 기존(최신순)과 100% 동일.
    if get_settings().feature_ads:
        q = q.order_by(Listing.is_sponsored.desc(), Listing.priority.desc(), Listing.created_at.desc())
    else:
        q = q.order_by(Listing.created_at.desc())
    rows = db.scalars(q.offset(offset).limit(limit)).all()
    return {"items": [_row_light(x) for x in rows], "count": len(rows),
            "offset": offset, "has_more": len(rows) >= limit}


@router.get("/{listing_id}")
def get_listing(listing_id: int, device_id: str = Query(""),
                db: Session = Depends(get_db), authorization: str | None = Header(None)):
    x = db.get(Listing, listing_id)
    if not x:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다.")
    acc = account_from_auth(db, authorization)
    is_owner = (acc and x.account_id and x.account_id == acc.id) \
        or (device_id and x.device_id and x.device_id == device_id)
    if x.status == "hidden" and not is_owner:   # 숨김 매물은 소유자만 조회(편집/복구용)
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다.")
    if not is_owner:   # 외부 조회만 집계(소유자 본인 조회는 제외). 원자 증가(경합 방지, read-modify-write 금지).
        db.execute(update(Listing).where(Listing.id == listing_id)
                   .values(views=func.coalesce(Listing.views, 0) + 1))
        db.commit()
        db.refresh(x)
    resp = _row_full(x)
    # '말릴 수 있는' 신호 — 이 매물 가격이 그 단지 실거래 대비 어디쯤인지(중개·광고 0이라 매물 위험도 솔직히).
    from app.services.pricecheck import listing_signal
    resp["market_signal"] = listing_signal(db, x.deal_type, x.complex_name, x.lawd_cd,
                                            x.price, x.deposit, x.exclusive_area,
                                            x.property_type or "apartment")
    return resp


@router.post("")
def create_listing(body: ListingIn, db: Session = Depends(get_db),
                   authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    # 로그인한 중개업자는 agent 매물로 강제(권한 일관성), 일반 계정은 폼 값 유지
    if acc and acc.role == "agent":
        body.poster_role = "agent"
    _validate(body)
    data = body.model_dump()
    data.pop("device_id", None)
    x = Listing(device_id=body.device_id, account_id=(acc.id if acc else None),
                created_at=datetime.utcnow(), **data)
    db.add(x)
    db.commit()
    db.refresh(x)
    return {"ok": True, "item": _row_full(x)}


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """매물 사진 업로드 → 외부/로컬 스토리지에 저장하고 공개 URL 반환.
    프런트는 이 URL을 매물의 photos 배열에 담아 등록한다(원본 base64 미저장)."""
    s = get_settings()
    if (file.content_type or "") not in storage.ALLOWED:
        raise HTTPException(status_code=415, detail="이미지 파일(jpg/png/webp/gif)만 업로드할 수 있습니다.")
    data = await file.read()
    if len(data) > s.upload_max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"이미지는 최대 {s.upload_max_mb}MB까지 가능합니다.")
    try:
        url = storage.save_image(data, file.content_type, file.filename)
    except Exception as e:  # noqa
        raise HTTPException(status_code=500, detail=f"업로드 실패: {e}")
    return {"url": url, "backend": s.storage_backend}


@router.delete("/{listing_id}")
def delete_listing(listing_id: int, device_id: str = Query(""),
                   db: Session = Depends(get_db),
                   authorization: str | None = Header(None)):
    x = db.get(Listing, listing_id)
    if not x:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다.")
    acc = account_from_auth(db, authorization)
    is_owner = (acc and x.account_id and x.account_id == acc.id) \
        or (device_id and x.device_id and x.device_id == device_id)
    if not is_owner:
        raise HTTPException(status_code=403, detail="등록자만 삭제할 수 있습니다.")
    x.status = "hidden"
    db.commit()
    return {"ok": True}


class StatusIn(BaseModel):
    status: str


@router.post("/{listing_id}/status")
def set_listing_status(listing_id: int, body: StatusIn, device_id: str = Query(""),
                       db: Session = Depends(get_db), authorization: str | None = Header(None)):
    """등록자만 매물 상태 변경: active(판매중)/traded(거래완료)/hidden(숨김)."""
    x = db.get(Listing, listing_id)
    if not x:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다.")
    acc = account_from_auth(db, authorization)
    is_owner = (acc and x.account_id and x.account_id == acc.id) \
        or (device_id and x.device_id and x.device_id == device_id)
    if not is_owner:
        raise HTTPException(status_code=403, detail="등록자만 변경할 수 있습니다.")
    if body.status not in ("active", "traded", "hidden"):
        raise HTTPException(status_code=400, detail="status는 active/traded/hidden 중 하나여야 합니다.")
    x.status = body.status
    db.commit()
    return {"ok": True, "status": x.status}


@router.put("/{listing_id}")
def update_listing(listing_id: int, body: ListingIn, device_id: str = Query(""),
                   db: Session = Depends(get_db), authorization: str | None = Header(None)):
    """등록자만 매물 수정. 폼 항목만 갱신(status/views/is_sponsored/등록일/소유자는 불변)."""
    x = db.get(Listing, listing_id)
    if not x:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다.")
    acc = account_from_auth(db, authorization)
    is_owner = (acc and x.account_id and x.account_id == acc.id) \
        or (device_id and x.device_id and x.device_id == device_id)
    if not is_owner:
        raise HTTPException(status_code=403, detail="등록자만 수정할 수 있습니다.")
    if acc and acc.role == "agent":
        body.poster_role = "agent"
    _validate(body)
    data = body.model_dump()
    data.pop("device_id", None)
    for k, v in data.items():   # ListingIn에는 status/views/is_sponsored가 없어 민감 필드는 보존됨
        setattr(x, k, v)
    db.commit()
    db.refresh(x)
    return {"ok": True, "item": _row_full(x)}
