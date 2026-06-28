"""구독/권한(entitlement) 게이팅 — 부록 B.

기본은 전원 free. `feature_monetization`·`feature_billing` 가 **모두 OFF**이면 항상 False를
반환해 프리미엄 게이팅이 비활성(= 현재와 동일하게 모든 기능 무료)이 되도록 한다.

플래그가 켜졌을 때만: 계정 plan=="premium" 또는 active 구독이 있으면 프리미엄으로 인정.
어떤 기존 기능도 기본값에서는 막지 않는다(구조만 준비).
"""
from app.core.config import get_settings


def is_premium(account, db=None) -> bool:
    """프리미엄 권한 여부. 플래그 ON + (plan=='premium' 또는 active 구독)일 때만 True."""
    s = get_settings()
    if not (s.feature_monetization or s.feature_billing):
        return False
    if account is None:
        return False
    if getattr(account, "plan", "free") == "premium":
        return True
    if db is not None:
        from app.services.billing import active_subscription
        return active_subscription(db, account) is not None
    return False


def require_premium(account, db=None) -> None:
    """프리미엄 전용 기능 게이트(필요할 때 사용). 권한 없으면 402."""
    from fastapi import HTTPException
    if not is_premium(account, db):
        raise HTTPException(status_code=402, detail="프리미엄 전용 기능입니다.")
