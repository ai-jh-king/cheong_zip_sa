"""외부 데이터 소스 '실연동' 상태 — 예시(sample) 화면을 사용자에게 보여주지 않기 위한 게이트.

배경(왜곡 없음): 키 미설정·활용신청 전이면 커넥터가 None → 화면이 예시 데이터로 채워진다.
배지로 구분해도 사용자는 "눌러봤더니 예시"를 반복 경험하면 다른 수치까지 의심하게 된다.
→ 실연동이 확인된 소스만 해당 UI를 노출하고, 아니면 그 탭·섹션 자체를 숨긴다.

구현: 외부 호출은 느릴 수 있어 `/config`(부팅 경로)에서 직접 호출하지 않는다.
      백그라운드(부팅 직후·스케줄러)에서 probe() 로 확인해 app_meta 에 저장하고,
      get() 은 DB 1회 읽기(빠름)만 한다.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.services import appmeta

logger = logging.getLogger(__name__)

KEY = "sources_live"
DEFAULT = {"subscription": False, "bank_rates": False, "places": False}


def get(db: Session) -> dict:
    """저장된 실연동 상태(없으면 전부 False = 숨김). 프로브 전에는 보수적으로 감춘다."""
    v = appmeta.get_json(db, KEY) or {}
    out = dict(DEFAULT)
    for k in DEFAULT:
        out[k] = bool(v.get(k))
    out["checked_at"] = v.get("checked_at")
    return out


def probe(db: Session) -> dict:
    """실제 커넥터를 호출해 실연동 여부를 갱신(백그라운드 전용). 실패는 False 로만 반영."""
    live = dict(DEFAULT)

    try:
        from app.sources.applyhome import fetch_subscriptions
        rows = fetch_subscriptions(limit=1)
        live["subscription"] = bool(rows)
    except Exception as e:  # noqa: BLE001
        logger.info("청약 소스 프로브 실패: %s", e)

    try:
        from app.sources.finlife import fetch_loan_products
        prods = fetch_loan_products(limit=1)
        live["bank_rates"] = bool(prods)
    except Exception as e:  # noqa: BLE001
        logger.info("은행금리 소스 프로브 실패: %s", e)

    try:
        from app.models import Place
        n = db.scalar(select(func.count()).select_from(Place)) or 0
        live["places"] = n > 0
    except Exception as e:  # noqa: BLE001
        logger.info("시설 데이터 확인 실패: %s", e)

    live["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    appmeta.set_json(db, KEY, live)
    logger.info("소스 실연동 상태: %s", live)
    return live
