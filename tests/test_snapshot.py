"""일일 집계 스냅샷 — 프리컴퓨트 저장 + 서빙/폴백/신선도 게이트(왜곡 없음).

핵심 검증:
- bake 가 board/ranking 을 저장한다.
- 엔드포인트가 (기본 파라미터일 때) 스냅샷을 서빙한다 — 저장분에 센티넬을 주입해 증명.
- 수집으로 data_version 이 오르면 오래된 스냅샷은 무시되고 라이브로 폴백한다(신선도 게이트).
- 비기본 파라미터는 스냅샷을 쓰지 않고 라이브로 계산한다.
"""
import json

from app.core import cache
from app.services import snapshot
from app.models import AggSnapshot


def _inject_sentinel(db, key, mark="SNAP"):
    """저장된 스냅샷 payload 에 센티넬을 심는다(엔드포인트가 스냅샷을 서빙했는지 증명용)."""
    row = db.get(AggSnapshot, key)
    p = json.loads(row.payload)
    p["_sentinel"] = mark
    row.payload = json.dumps(p, ensure_ascii=False)
    db.commit()
    return mark


def test_bake_stores_targets(client, db):
    res = snapshot.bake(db)
    assert res["baked"] == res["targets"] == 2
    assert db.get(AggSnapshot, snapshot.BOARD_KEY) is not None
    assert db.get(AggSnapshot, snapshot.RANKING_KEY) is not None


def test_board_serves_snapshot(client, db):
    snapshot.bake(db)
    _inject_sentinel(db, snapshot.BOARD_KEY)
    r = client.get("/dashboard/board?property_type=apartment").json()
    assert r.get("_sentinel") == "SNAP"          # 스냅샷을 서빙(라이브였다면 센티넬 없음)


def test_ranking_serves_snapshot_default_params_only(client, db):
    snapshot.bake(db)
    _inject_sentinel(db, snapshot.RANKING_KEY, "R")
    # 기본(apartment·60·all)만 스냅샷 서빙
    hit = client.get("/dashboard/ranking?property_type=apartment&limit=60&area_band=all").json()
    assert hit.get("_sentinel") == "R"
    # 다른 파라미터는 라이브 계산(스냅샷 무시)
    miss = client.get("/dashboard/ranking?property_type=apartment&limit=15&area_band=all").json()
    assert "_sentinel" not in miss


def test_stale_snapshot_falls_back_to_live(client, db):
    snapshot.bake(db)
    _inject_sentinel(db, snapshot.BOARD_KEY)
    cache.bump_data_version()                     # 수집 발생 → 스냅샷은 오래됨
    r = client.get("/dashboard/board?property_type=apartment").json()
    assert "_sentinel" not in r                   # 라이브 폴백(신선도 게이트)
    assert r["property_type"] == "apartment"      # 라이브 응답 정상


def test_get_fresh_missing_key(db):
    assert snapshot.get_fresh(db, "nope:key") is None


def test_non_default_property_type_uses_live(client, db):
    snapshot.bake(db)
    _inject_sentinel(db, snapshot.BOARD_KEY)
    # officetel 은 스냅샷 대상 아님 → 라이브
    r = client.get("/dashboard/board?property_type=officetel").json()
    assert "_sentinel" not in r
    assert r["property_type"] == "officetel"
