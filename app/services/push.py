"""웹푸시(VAPID) 발송 서비스. VAPID 키 없으면 무동작(no-op).

- 브라우저 PushManager 구독(endpoint+p256dh+auth)을 PushSubscription 에 저장.
- pywebpush 로 발송(지연 import → 패키지 없거나 키 없으면 앱은 정상 기동).
- 만료(404/410) 구독은 disabled 처리해 자동 정리. 연속 실패 누적 시도 정리.
- 향후 FCM/APNs(token) 채널 추가 가능(현재는 webpush만 구현).
"""
from __future__ import annotations
import json
import logging
from datetime import datetime

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import PushSubscription, DeviceLink

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    return get_settings().push_enabled


def public_key() -> str | None:
    return get_settings().vapid_public_key or None


def _send_one_webpush(sub: PushSubscription, payload: dict) -> str:
    """반환: 'ok' | 'gone'(만료/삭제됨) | 'fail'."""
    from pywebpush import webpush, WebPushException  # lazy import
    s = get_settings()
    try:
        webpush(
            subscription_info={"endpoint": sub.endpoint,
                               "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=s.vapid_private_key,
            vapid_claims={"sub": s.vapid_subject},
            timeout=10,
        )
        return "ok"
    except WebPushException as e:  # noqa
        code = getattr(getattr(e, "response", None), "status_code", None)
        if code in (404, 410):
            return "gone"
        logger.warning("웹푸시 실패(status=%s): %s", code, e)
        return "fail"
    except Exception as e:  # noqa
        logger.warning("웹푸시 예외: %s", e)
        return "fail"


def dispatch(db: Session, subs: list[PushSubscription], payload: dict) -> dict:
    """구독 목록으로 발송 + 상태 갱신(만료/실패 정리). 비활성·중복은 건너뜀."""
    if not is_enabled() or not subs:
        return {"sent": 0, "gone": 0, "fail": 0, "skipped": len(subs), "enabled": is_enabled()}
    sent = gone = fail = 0
    for sub in subs:
        if sub.disabled or sub.channel != "webpush" or not sub.p256dh or not sub.auth:
            continue
        r = _send_one_webpush(sub, payload)
        if r == "ok":
            sent += 1
            sub.last_ok_at = datetime.utcnow()
            sub.fail_count = 0
        elif r == "gone":
            gone += 1
            sub.disabled = True
        else:
            fail += 1
            sub.fail_count = (sub.fail_count or 0) + 1
            if sub.fail_count >= 8:
                sub.disabled = True
    db.commit()
    return {"sent": sent, "gone": gone, "fail": fail, "skipped": 0, "enabled": True}


def _account_device_ids(db: Session, account_id: int) -> list[str]:
    return list(db.scalars(select(DeviceLink.device_id)
                           .where(DeviceLink.account_id == account_id)).all())


def dispatch_to_account(db: Session, account_id: int, payload: dict) -> dict:
    """계정의 활성 구독으로 발송(account_id 직접 매칭 + 연결된 device_id 모두)."""
    if not is_enabled():
        return {"sent": 0, "skipped": 0, "enabled": False}
    devs = _account_device_ids(db, account_id)
    cond = [PushSubscription.account_id == account_id]
    if devs:
        cond.append(PushSubscription.device_id.in_(devs))
    subs = list(db.scalars(select(PushSubscription)
                           .where(PushSubscription.disabled.is_(False))
                           .where(or_(*cond))).all())
    uniq = {s.endpoint: s for s in subs}          # endpoint 중복 제거
    return dispatch(db, list(uniq.values()), payload)


def dispatch_to_device(db: Session, device_id: str, payload: dict) -> dict:
    """단일 기기의 활성 구독으로 발송(테스트/비로그인 알림용)."""
    if not is_enabled():
        return {"sent": 0, "skipped": 0, "enabled": False}
    subs = list(db.scalars(select(PushSubscription)
                           .where(PushSubscription.device_id == device_id)
                           .where(PushSubscription.disabled.is_(False))).all())
    return dispatch(db, subs, payload)
