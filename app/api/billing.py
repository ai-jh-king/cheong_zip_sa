"""결제/구독 API — 첫 매출(B2B) 결제 경로.

전 엔드포인트 **feature_billing ON일 때만** 동작(기본 OFF → 404 '비활성').
플래그 OFF면 구독/결제 자체가 노출되지 않으므로 서비스 초반 동작은 현재와 100% 동일.

provider=mock이면 키 없이 흐름 검증 가능(confirm 즉시 활성). 실제 PG는 키 설정 후 구현.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings
from app.api.auth import account_from_auth
from app.models import Subscription
from app.services import billing
from app.services.entitlement import is_premium

router = APIRouter(prefix="/billing", tags=["billing"])


def _require_billing():
    if not get_settings().feature_billing:
        raise HTTPException(status_code=404, detail="결제 기능이 비활성화되어 있습니다.")


def _require_account(db, authorization):
    acc = account_from_auth(db, authorization)
    if not acc:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return acc


class CheckoutIn(BaseModel):
    plan: str = "agent_pro"


class ConfirmIn(BaseModel):
    plan: str = "agent_pro"
    token: str | None = None
    provider_ref: str | None = None


@router.get("/plans")
def list_plans():
    """플랜 목록. feature_billing OFF면 enabled=false 만 반환(프런트가 UI 숨김)."""
    if not get_settings().feature_billing:
        return {"enabled": False, "plans": []}
    return {"enabled": True, "provider": get_settings().billing_provider or "mock",
            "plans": list(billing.PLANS.values())}


@router.get("/me")
def my_subscription(db: Session = Depends(get_db), authorization: str | None = Header(None)):
    """내 구독 상태. 비활성이어도 200(enabled=false)으로 안전 반환."""
    if not get_settings().feature_billing:
        return {"enabled": False, "premium": False, "subscription": None}
    acc = account_from_auth(db, authorization)
    if not acc:
        return {"enabled": True, "premium": False, "subscription": None}
    sub = billing.active_subscription(db, acc)
    return {
        "enabled": True,
        "premium": is_premium(acc, db),
        "subscription": ({
            "plan": sub.plan, "status": sub.status, "provider": sub.provider,
            "started_at": sub.started_at.isoformat() if sub.started_at else None,
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
        } if sub else None),
    }


@router.post("/checkout")
def checkout(body: CheckoutIn, db: Session = Depends(get_db), authorization: str | None = Header(None)):
    """결제 시작. mock이면 confirm_token 반환 → 프런트가 /confirm 호출."""
    _require_billing()
    acc = _require_account(db, authorization)
    try:
        return {"ok": True, **billing.create_checkout(body.plan, acc)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/confirm")
def confirm(body: ConfirmIn, db: Session = Depends(get_db), authorization: str | None = Header(None)):
    """결제 확인 → 구독 활성화. 실제 PG는 서버검증 후 호출되어야 함(mock은 토큰 확인)."""
    _require_billing()
    acc = _require_account(db, authorization)
    try:
        sub = billing.confirm_checkout(db, acc, body.plan, body.token, body.provider_ref)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "premium": True, "plan": sub.plan,
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None}


@router.post("/cancel")
def cancel(db: Session = Depends(get_db), authorization: str | None = Header(None)):
    """구독 취소(active → canceled). 만료까지는 권한 유지 정책은 추후."""
    _require_billing()
    acc = _require_account(db, authorization)
    subs = db.execute(
        select(Subscription).where(Subscription.account_id == acc.id, Subscription.status == "active")
    ).scalars().all()
    n = 0
    for sub in subs:
        sub.status = "canceled"
        n += 1
    if n:
        try:
            acc.plan = "free"
        except Exception:
            pass
        db.commit()
    return {"ok": True, "canceled": n}
