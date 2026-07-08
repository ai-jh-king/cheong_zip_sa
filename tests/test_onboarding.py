"""전입자 온보딩 추천 — 조립 로직(통근 근접 + 시세 + 예산 차액) 단위 테스트.
(샌드박스는 httpx 미설치로 실행 불가하나 compile 통과. 실행은 사용자 pytest.)"""
from datetime import date

from app.models import CommuteDestination, Complex, Transaction
from app.services import onboarding as ob


def _cx(db, name, lawd, lat, lng):
    c = Complex(name=name, lawd_cd=lawd, property_type="apartment", lat=lat, lng=lng)
    db.add(c)
    db.flush()
    return c


def _tx(name, lawd, amount, key):
    return Transaction(lawd_cd=lawd, property_type="apartment", deal_type="trade",
                       complex_name=name, exclusive_area=84.9, floor=7,
                       contract_date=date(2026, 5, 1), deal_amount=amount,
                       source="TEST", dedup_key=key)


def _seed(db):
    db.add(CommuteDestination(key="sk_hynix_cheongju", name="SK하이닉스 청주캠퍼스",
                              category="job", lat=36.6750, lng=127.4250,
                              gu="흥덕구", is_active=True, sort_order=1))
    # 가까운 단지(가격 있음) / 조금 먼 단지(가격 있음)
    _cx(db, "가까운단지", "43113", 36.6760, 127.4260)
    _cx(db, "먼단지", "43113", 36.7050, 127.4600)
    for i, a in enumerate([50000, 52000, 51000]):
        db.add(_tx("가까운단지", "43113", a, f"near{i}"))
    for i, a in enumerate([80000, 82000]):
        db.add(_tx("먼단지", "43113", a, f"far{i}"))
    db.commit()


def test_onboarding_options_lists_jobs(db):
    _seed(db)
    opts = ob.options(db)["destinations"]
    assert any(d["key"] == "sk_hynix_cheongju" for d in opts)


def test_onboarding_recommend_assembles_price_and_sorts_by_commute(db):
    _seed(db)
    res = ob.recommend(db, "sk_hynix_cheongju", budget=60000, max_minutes=60)
    assert res["destination"]["name"].startswith("SK하이닉스")
    items = res["items"]
    assert items, "직장 근처 단지가 나와야 함"
    # 가격(실거래 중앙값) 결합
    near = next(x for x in items if x["name"] == "가까운단지")
    assert near["latest_amount"] is not None
    # 예산 차액(왜곡 없음: 판정 아닌 차액). 5.1억 - 6억 = 음수(자기자본 이내)
    assert near["over_budget_by"] is not None and near["over_budget_by"] < 0
    # 통근시간 짧은 순 정렬(가격 있는 것 우선)
    mins = [x["minutes"] for x in items if x["latest_amount"] is not None]
    assert mins == sorted(mins)
    # 정체성 고지(중개·광고 없음) 포함
    assert "권유하지 않습니다" in res["notice"]


def test_onboarding_recommend_unknown_dest_is_safe(db):
    res = ob.recommend(db, "no_such_key")
    assert res["items"] == [] and res["destination"] is None
