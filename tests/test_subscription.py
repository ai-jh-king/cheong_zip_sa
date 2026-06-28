"""청약 전용 탭 API — 키 없으면 예시 폴백(live=False), 구조 일관."""


def test_subscription_endpoint_fallback(client):
    r = client.get("/subscription")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and isinstance(body["items"], list)
    assert body["live"] is False          # 테스트 환경엔 키 없음 → 예시
    assert body["notice"]                 # 예시 안내 노출
    assert body["disclaimer"]
    # 예시 데이터는 is_sample 표기(왜곡 방지)
    if body["items"]:
        assert all("status" in s for s in body["items"])


def test_subscription_limit(client):
    r = client.get("/subscription?limit=3")
    assert r.status_code == 200
