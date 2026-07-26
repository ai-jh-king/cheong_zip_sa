"""집사 도감 API — 시리즈/편 공개 조회 · 관리자 CRUD · 조회수 원자 증가 · 초안 비노출."""
from app.models import Guide, GuideSeries

ADMIN = {"X-Admin-Token": "test-admin-token"}


def _seed(db, n=2):
    # 멱등: 앱 startup 자동 시드(집사 도감)가 이미 시리즈를 넣었을 수 있음
    if not db.get(GuideSeries, "cheongju"):
        db.add(GuideSeries(key="cheongju", name="집사가 알려주는 청주",
                           description="실사용 안내서", cover_emoji="🏘", sort_order=1))
    for i in range(n):
        db.add(Guide(series_key="cheongju", title=f"{i+1}편 제목", body_md=f"# 제목 {i+1}\n\n본문입니다.",
                     sort_order=i + 1, is_published=True))
    db.commit()


def test_series_list_and_counts(client, db):
    _seed(db)
    j = client.get("/guides/series").json()
    assert j["series"][0]["key"] == "cheongju"
    assert j["series"][0]["guide_count"] == 2
    assert "권유하지 않습니다" in j["notice"]          # 정체성 고지


def test_series_detail_excludes_draft(client, db):
    _seed(db)
    db.add(Guide(series_key="cheongju", title="초안", body_md="아직 검수 전 초안입니다.",
                 is_published=False))
    db.commit()
    j = client.get("/guides/series/cheongju").json()
    assert len(j["guides"]) == 2                      # 초안 제외
    assert all("body_md" not in g for g in j["guides"])   # 목록은 본문 미포함(가볍게)


def test_guide_detail_with_prev_next(client, db):
    _seed(db, n=3)
    ids = [g["id"] for g in client.get("/guides/series/cheongju").json()["guides"]]
    j = client.get(f"/guides/{ids[1]}").json()
    assert j["guide"]["body_md"].startswith("# 제목")
    assert j["prev"]["id"] == ids[0] and j["next"]["id"] == ids[2]


def test_view_count_atomic(client, db):
    _seed(db, n=1)
    gid = client.get("/guides/series/cheongju").json()["guides"][0]["id"]
    for _ in range(3):
        client.post(f"/guides/{gid}/view")
    assert client.get(f"/guides/{gid}").json()["guide"]["view_count"] == 3


def test_admin_disabled_without_token_config(client, db):
    """ADMIN_TOKEN 미설정(테스트 기본)이면 관리자 기능 503(비활성)."""
    _seed(db, n=0)
    body = {"series_key": "cheongju", "title": "새 편", "body_md": "본문 열 자 이상입니다."}
    assert client.post("/admin/guides", json=body).status_code == 503


def test_admin_crud_requires_token(client, db, monkeypatch):
    _seed(db, n=0)
    from app.api import guides as gmod

    class _S:
        admin_token = "test-admin-token"
    monkeypatch.setattr(gmod, "get_settings", lambda: _S())
    body = {"series_key": "cheongju", "title": "새 편", "body_md": "본문 열 자 이상입니다."}
    assert client.post("/admin/guides", json=body).status_code == 401       # 토큰 없음
    r = client.post("/admin/guides", json=body, headers=ADMIN)
    assert r.status_code == 200
    gid = r.json()["guide"]["id"]
    r2 = client.put(f"/admin/guides/{gid}", json={**body, "title": "수정된 편"}, headers=ADMIN)
    assert r2.json()["guide"]["title"] == "수정된 편"
    assert client.delete(f"/admin/guides/{gid}", headers=ADMIN).json()["ok"] is True
    assert client.get(f"/guides/{gid}").status_code == 404
