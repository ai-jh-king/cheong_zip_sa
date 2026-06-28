"""결제/구독 서비스 — provider 추상화.

설계:
- feature_billing OFF가 기본이라, 라우터에서 플래그로 막는다. 본 모듈은 '어떻게' 결제하는지만 담당.
- provider: mock(키 없이 흐름 검증) / toss / portone. 실제 PG는 키·웹훅 검증이 필요하므로
  toss/portone는 '키 필요' 응답을 돌려주는 스텁(운영자가 키 설정 후 구현부 채움).
- 플랜·가격은 설정값. 정책 변경 시 여기만 수정. 금액은 원(KRW).
"""
from __future__ import annotations
from datetime import datetime, timedelta
import secrets

from app.core.config import get_settings
from app.models import Subscription

# 플랜 정의(설정값) — 첫 매출=중개사 대상 'agent_pro'
PLANS = {
    "agent_pro": {
        "id": "agent_pro",
        "name": "중개사 Pro",
        "price": 19000,            # 원/월 (예시 — 운영 시 확정)
        "period_days": 30,
        "perks": [
            "받은 문의(리드) 전체 연락처 열람",
            "매물 상위 노출(광고 기능 활성 시)",
            "대시보드 통계 확장",
        ],
    },
}


def get_plan(plan_id: str) -> dict | None:
    return PLANS.get(plan_id)


def create_checkout(plan_id: str, account) -> dict:
    """결제 시작. 반환값을 프런트가 사용해 결제창/확인으로 진행.

    - mock: confirm_token 발급 → 프런트가 /billing/confirm 호출(즉시 활성).
    - toss/portone: 키 필요(스텁). 실제 구현 시 결제창 파라미터/redirect 반환.
    """
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError("알 수 없는 플랜입니다.")
    provider = get_settings().billing_provider or "mock"
    base = {"provider": provider, "plan": plan_id, "amount": plan["price"]}
    if provider == "mock":
        return {**base, "mode": "mock", "confirm_token": "mock_" + secrets.token_hex(8),
                "message": "테스트(mock) 결제입니다. 확인을 누르면 즉시 구독이 활성화됩니다."}
    # 실제 PG: 키·SDK 필요 → 스텁
    return {**base, "mode": "redirect", "configured": False,
            "message": f"{provider} 연동 키가 설정되지 않았습니다. 운영자가 키 설정 후 결제창 연동을 구현해야 합니다."}


def confirm_checkout(db, account, plan_id: str, token: str | None, provider_ref: str | None) -> Subscription:
    """결제 확인 → 구독 활성화. mock은 토큰만 확인. 실제 PG는 결제 검증 후 호출되어야 함."""
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError("알 수 없는 플랜입니다.")
    provider = get_settings().billing_provider or "mock"
    if provider == "mock":
        if not token or not token.startswith("mock_"):
            raise ValueError("결제 토큰이 올바르지 않습니다.")
    else:
        # 실제 PG: provider_ref(주문/결제 키)로 서버-서버 검증이 선행되어야 함(스텁)
        raise ValueError(f"{provider} 결제 검증이 구현되지 않았습니다(키 설정 필요).")

    now = datetime.utcnow()
    sub = Subscription(
        account_id=account.id,
        plan=plan_id,
        status="active",
        provider=provider,
        provider_ref=provider_ref or token,
        amount=plan["price"],
        started_at=now,
        expires_at=now + timedelta(days=plan["period_days"]),
    )
    db.add(sub)
    # 계정 plan 갱신(빠른 권한 판정용 — entitlement는 active 구독도 함께 확인)
    try:
        account.plan = "premium"
    except Exception:
        pass
    db.commit()
    db.refresh(sub)
    return sub


def active_subscription(db, account):
    """계정의 유효(active·미만료) 구독 1건 반환(없으면 None)."""
    if not account:
        return None
    from sqlalchemy import select
    now = datetime.utcnow()
    rows = db.execute(
        select(Subscription).where(Subscription.account_id == account.id,
                                   Subscription.status == "active")
        .order_by(Subscription.expires_at.desc())
    ).scalars().all()
    for s in rows:
        if s.expires_at is None or s.expires_at > now:
            return s
    return None
