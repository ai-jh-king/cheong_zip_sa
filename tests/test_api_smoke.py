"""핵심 엔드포인트 스모크 — 200/정상 응답(데이터 없어도 깨지지 않아야)."""


def test_openapi(client):
    assert client.get("/openapi.json").status_code == 200


def test_root_ui_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "html" in r.headers.get("content-type", "").lower()


def test_community_categories(client):
    r = client.get("/community/categories")
    assert r.status_code == 200


def test_community_posts_empty(client):
    r = client.get("/community/posts")
    assert r.status_code == 200
    assert "items" in r.json()


def test_search_runs(client):
    r = client.get("/search", params={"q": "테스트"})
    assert r.status_code == 200
