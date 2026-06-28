"""커뮤니티 API — 원자적 카운터(조회·좋아요·신고)·스크랩 동작.
로그인 없이 device_id 소유권으로 검증(좋아요/신고/스크랩은 비로그인 허용)."""
from datetime import datetime
from app.models import Post


def _make_post(db):
    p = Post(account_id=1, device_id="owner", nickname="작성자",
             category="free", title="테스트 제목입니다", body="테스트 본문입니다",
             created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.id


def test_views_increment_is_atomic(client, db):
    pid = _make_post(db)
    v1 = client.get(f"/community/posts/{pid}?device_id=x").json()["post"]["views"]
    client.get(f"/community/posts/{pid}?device_id=x")
    v3 = client.get(f"/community/posts/{pid}?device_id=x").json()["post"]["views"]
    assert v3 == v1 + 2


def test_like_toggle_counts(client, db):
    pid = _make_post(db)
    on = client.post(f"/community/posts/{pid}/like", json={"device_id": "u1"}).json()
    assert on["liked"] is True and on["like_count"] == 1
    off = client.post(f"/community/posts/{pid}/like", json={"device_id": "u1"}).json()
    assert off["liked"] is False and off["like_count"] == 0


def test_bookmark_toggle_and_list(client, db):
    pid = _make_post(db)
    assert client.post(f"/community/posts/{pid}/bookmark", json={"device_id": "u1"}).json()["bookmarked"] is True
    items = client.get("/community/bookmarks?device_id=u1").json()["items"]
    assert any(it["id"] == pid for it in items)


def test_report_threshold_hides_post(client, db):
    pid = _make_post(db)
    for i in range(5):                       # REPORT_HIDE=5
        client.post(f"/community/posts/{pid}/report", json={"device_id": f"d{i}"})
    assert client.get(f"/community/posts/{pid}").status_code == 404   # 숨김 처리됨
