"""일일 집계 스냅샷 — 무거운 대시보드 집계를 요청 경로 밖(cron 수집 후·워밍업)에서
미리 계산해 저장하고, 웹은 '읽기 1회'로 즉시 응답한다.

배경: 이 앱의 원천 데이터는 하루 1회(새벽 수집)만 바뀐다. 그런데 board(집계 11종)·
ranking(7종)을 매 요청(또는 캐시 만료마다) 즉석 계산 → free PG·저사양에서 첫 로드가 느림.
바뀌지도 않는 걸 반복 계산하지 말고, 수집 직후 1번만 구워 저장한다.

왜곡 없음: 스냅샷에 data_version·baked_at 을 함께 기록. 서빙 시 현재 data_version 과
일치할 때만 사용하고, 불일치(수집됐는데 아직 미갱신)면 None → 호출부가 라이브 계산으로 폴백.
따라서 '라이브보다 오래된' 집계를 내보내지 않는다.
"""
import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.cache import get_data_version
from app.models import AggSnapshot

log = logging.getLogger(__name__)

# 스냅샷 대상 = 프런트 첫 로드의 무거운 두 집계(기본 파라미터). 다른 파라미터 조합은
# 사용자가 전환할 때만 쓰이고 빈도가 낮아 라이브(캐시)로 충분 → 스냅샷 대상에서 제외.
BOARD_KEY = "board:apartment"
RANKING_KEY = "ranking:apartment:60:all"


def get_fresh(db: Session, key: str):
    """현재 data_version 과 일치하는 스냅샷만 dict 로 반환. 없거나 오래됐으면 None(라이브 폴백)."""
    row = db.get(AggSnapshot, key)
    if not row or row.data_version != get_data_version():
        return None
    try:
        return json.loads(row.payload)
    except Exception:  # noqa - 손상 페이로드는 무시하고 라이브 폴백
        return None


def put(db: Session, key: str, payload: dict) -> None:
    """페이로드를 현재 data_version 도장을 찍어 upsert."""
    dv = get_data_version()
    js = json.dumps(payload, ensure_ascii=False, default=str)
    row = db.get(AggSnapshot, key)
    if row:
        row.payload, row.data_version, row.baked_at = js, dv, datetime.utcnow()
    else:
        db.add(AggSnapshot(key=key, payload=js, data_version=dv,
                           baked_at=datetime.utcnow()))
    db.commit()


def bake(db: Session) -> dict:
    """수집 직후(cron)·워밍업(부팅)에서 호출. board/ranking(apartment 기본)을 구워 저장.
    개별 실패는 삼켜 서비스에 영향 없음(해당 키는 다음 요청 때 라이브 폴백)."""
    from app.api import dashboard  # 지연 import(순환 회피)
    targets = [
        (BOARD_KEY, lambda: dashboard.build_board(db, "apartment")),
        (RANKING_KEY, lambda: dashboard.build_ranking(db, "apartment", 60, "all")),
    ]
    baked = 0
    for key, builder in targets:
        try:
            put(db, key, builder())
            baked += 1
        except Exception as e:  # noqa
            log.warning("스냅샷 굽기 실패 %s: %s", key, e)
    dv = get_data_version()
    log.info("집계 스냅샷 %d/%d 갱신(data_version=%s)", baked, len(targets), dv)
    return {"baked": baked, "targets": len(targets), "data_version": dv}
