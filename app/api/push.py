"""웹푸시 구독/해지/테스트 API.

- GET  /push/vapid       : 공개 VAPID 키 + 활성여부(프런트가 구독 시 사용)
- POST /push/subscribe   : 브라우저 구독 저장(endpoint 기준 멱등). 로그인 시 account 연결
- POST /push/unsubscribe : endpoint 로 구독 삭제
- POST /push/test        : 해당 device 의 구독으로 테스트 푸시
"""
from fastapi import APIRouter, Depends, Header, Body
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import PushSubscription
from app.services import push
from app.api.auth import account_from_auth

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/vapid")
def vapid():
    return {"publicKey": push.public_key(), "enabled": push.is_enabled()}


@router.post("/subscribe")
def subscribe(payload: dict = Body(...), authorization: str | None = Header(None),
              db: Session = Depends(get_db)):
    device_id = (payload.get("device_id") or "").strip()
    sub = payload.get("subscription") or {}
    endpoint = sub.get("endpoint")
    keys = sub.get("keys") or {}
    if not device_id or not endpoint:
        return {"ok": False, "error": "device_id와 subscription이 필요합니다."}
    acc = account_from_auth(db, authorization)
    acct_id = acc.id if acc else None
    row = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
    if row:
        row.device_id = device_id
        row.account_id = acct_id
        row.p256dh = keys.get("p256dh")
        row.auth = keys.get("auth")
        row.disabled = False
        row.fail_count = 0
    else:
        db.add(PushSubscription(
            device_id=device_id, account_id=acct_id, channel="webpush",
            endpoint=endpoint, p256dh=keys.get("p256dh"), auth=keys.get("auth"),
            user_agent=(payload.get("user_agent") or "")[:200]))
    db.commit()
    return {"ok": True, "enabled": push.is_enabled()}


@router.post("/unsubscribe")
def unsubscribe(payload: dict = Body(...), db: Session = Depends(get_db)):
    endpoint = payload.get("endpoint") or ""
    if endpoint:
        db.execute(delete(PushSubscription).where(PushSubscription.endpoint == endpoint))
        db.commit()
    return {"ok": True}


@router.post("/test")
def test(payload: dict = Body(default={}), db: Session = Depends(get_db)):
    device_id = (payload.get("device_id") or "").strip()
    if not device_id:
        return {"ok": False, "error": "device_id가 필요합니다."}
    res = push.dispatch_to_device(db, device_id, {
        "title": "청주집사 알림 테스트",
        "body": "푸시가 정상적으로 동작합니다 🎉",
        "url": "/"})
    return {"ok": True, "result": res}
