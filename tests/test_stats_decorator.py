"""회귀: 집계 캐시 데코레이터(@stat_cached) 이중 적용 → 데드락 방지.

배경(v1.66 수정):
  stats.trending_complexes 에 @stat_cached 가 '두 번' 적용돼 있었다.
  stat_cached 의 캐시 키는 fn.__qualname__ 기준이라 두 겹이 '같은 키'를 쓴다.
  캐시 미스 시 바깥 wrapper 가 키 K 의 비재진입 락을 잡은 채 loader 로
  안쪽 wrapper 를 부르고, 안쪽이 같은 키 K 의 같은 락을 재획득하려다 → 데드락.
  영향: 홈 대시보드(GET /dashboard/board)가 각 데이터 버전마다 '첫 요청'에서 멈춤.

이 모듈은 두 각도로 재발을 막는다.
  1) 구조 검사: app 전체에 '연속 동일 데코레이터'가 0건이어야 한다(부류 전체 차단).
  2) 동작 검사: trending_complexes 가 캐시 미스 경로에서 데드락 없이 반환한다
     (데몬 스레드 + 타임아웃으로 CI 가 매달리지 않게 fail-fast).
"""
from __future__ import annotations

import glob
import os
import threading
from datetime import date, timedelta
from pathlib import Path

from app.models import Transaction
from app.services import stats
from app.core import cache

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_no_duplicate_stacked_decorators_in_app():
    """연속으로 동일한 데코레이터가 두 번 붙은 곳이 있으면 실패(이중 캐싱·데드락 신호)."""
    dups: list[str] = []
    for f in glob.glob(str(_REPO_ROOT / "app" / "**" / "*.py"), recursive=True):
        lines = Path(f).read_text(encoding="utf-8").split("\n")
        for i in range(len(lines) - 1):
            a, b = lines[i].strip(), lines[i + 1].strip()
            if a.startswith("@") and a == b:
                rel = os.path.relpath(f, _REPO_ROOT)
                dups.append(f"{rel}:{i + 1} {a}")
    assert dups == [], f"연속 중복 데코레이터 발견(제거 필요): {dups}"


def _seed_trending(db) -> None:
    """직전 90일 대비 최근 90일 거래가 늘어난 단지 1개를 시드(거래 급상승 신호)."""
    today = date.today()
    rows = []
    for i in range(3):  # 최근 90일: 3건
        rows.append(Transaction(
            lawd_cd="43111", property_type="apartment", deal_type="trade",
            complex_name="급상승단지", exclusive_area=84.9, floor=5,
            contract_date=today - timedelta(days=10 + i),
            deal_amount=50000 + i, source="TEST", dedup_key=f"rt_recent_{i}",
            is_canceled=False))
    rows.append(Transaction(  # 직전 90일: 1건
        lawd_cd="43111", property_type="apartment", deal_type="trade",
        complex_name="급상승단지", exclusive_area=84.9, floor=5,
        contract_date=today - timedelta(days=120),
        deal_amount=49000, source="TEST", dedup_key="rt_prev_0", is_canceled=False))
    db.add_all(rows)
    db.commit()


def test_trending_complexes_returns_without_deadlock(db):
    """캐시 미스 경로(데이터 버전 무효화 직후)에서 데드락 없이 dict 를 반환해야 한다."""
    _seed_trending(db)
    cache.bump_data_version()  # 캐시 무효화 → 반드시 락 경로(get_or_set)로 진입

    box: dict = {}

    def run():
        box["result"] = stats.trending_complexes(db, "apartment", 8)

    t = threading.Thread(target=run, daemon=True)  # daemon: 회귀 시에도 CI 종료 보장
    t.start()
    t.join(timeout=5.0)

    assert not t.is_alive(), "trending_complexes 가 5초 내 반환하지 않음 — 데드락(이중 데코레이터) 의심"
    result = box.get("result")
    assert isinstance(result, dict)
    assert result.get("basis") in ("surge", "active")
    assert isinstance(result.get("items"), list)
    # 시드한 '급상승단지'(최근 3건·직전 1건)가 한 항목으로 집계돼야 한다(빈 폴백이 아님).
    assert any(it["name"] == "급상승단지" for it in result["items"])
