"""정책대출 매칭 — 3단 평가(충족/미충족/확인필요)·판정 금지·면책(왜곡 없음)."""
from app.services import policyloan


def test_match_pass_and_fail():
    r = policyloan.match("buy", income=5000, newlywed=False, kids2=False,
                         newborn=False, homeless=True, amount=30000)
    assert r["disclaimer"] and r["as_of"]
    by = {x["key"]: x for x in r["items"]}
    assert by["didimdol"]["overall"] == "pass"          # 소득 5천·3억·무주택 → 디딤돌 요건 충족 가능성
    assert by["newborn"]["overall"] == "fail"           # 출산 요건 미해당
    # 전세 상품(버팀목)은 구입 목적에서 제외
    assert "beotimmok" not in by


def test_match_unknown_income():
    r = policyloan.match("jeonse", income=None, homeless=None, amount=15000)
    by = {x["key"]: x for x in r["items"]}
    assert by["beotimmok"]["overall"] == "maybe"        # 미입력 → 확인 필요(단정 금지)
    states = {c["state"] for c in by["beotimmok"]["checks"]}
    assert "unknown" in states


def test_match_newlywed_boost():
    # 신혼 소득 완화: 일반 6천 초과·신혼 8.5천 이하 → 디딤돌 소득 요건 pass
    r = policyloan.match("buy", income=8000, newlywed=True, homeless=True, amount=55000)
    by = {x["key"]: x for x in r["items"]}
    inc = [c for c in by["didimdol"]["checks"] if "연소득" in c["label"]][0]
    assert inc["state"] == "pass"
    price = [c for c in by["didimdol"]["checks"] if "주택 가격" in c["label"]][0]
    assert price["state"] == "pass"                     # 신혼 6억 완화


def test_protection_rules_api(client, db):
    j = client.get("/loan/protection-rules").json()
    assert j["soak"]["table"][0]["deposit_max"] == 7500
    assert "설정일" in j["soak"]["note"]                 # 담보물권 설정일 기준 주의문
    assert any(i["key"] == "deposit_cap" for i in j["hug"]["items"])
    assert len(j["bank_links"]) >= 5


def test_policy_match_api(client, db):
    j = client.post("/loan/policy-match", json={"purpose": "buy", "income": 5000,
                                                "homeless": True, "amount": 30000}).json()
    assert j["items"] and j["disclaimer"]
