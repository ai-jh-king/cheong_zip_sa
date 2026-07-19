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


def test_post_resident_badge_requires_matching_my_home(client, db):
    """주민 뱃지: 자가 신고가 아니라 서버가 '우리집(prefs.my_home)'과 대조해 저장(왜곡 없음)."""
    from app.models import UserPref
    # dev-login → 계정 + device 링크 자동 생성(test_account_delete.py 패턴)
    r = client.post("/auth/dev-login", json={"device_id": "dev-res1", "nickname": "주민1"})
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"dev-login 실패: {r.json()}"
    h = {"Authorization": f"Bearer {tok}"}
    # 그 기기의 prefs에 우리집 설정
    db.add(UserPref(device_id="dev-res1",
                    data={"my_home": {"complex_name": "청주더샵", "lawd_cd": "43113"}}))
    db.commit()
    # ① 우리집과 같은 단지 태그 → resident True
    r1 = client.post("/community/posts", headers=h, json={
        "title": "우리 단지 주차 얘기", "body": "주차 어렵네요", "category": "free",
        "complex_name": "청주더샵", "lawd_cd": "43113"})
    assert r1.status_code == 200, r1.text
    assert r1.json()["post"].get("resident") is True
    # ② 다른 단지 태그 → resident False (뱃지 못 받음)
    r2 = client.post("/community/posts", headers=h, json={
        "title": "다른 단지 질문", "body": "여기 어때요?", "category": "qa",
        "complex_name": "다른아파트", "lawd_cd": "43111"})
    assert r2.status_code == 200 and r2.json()["post"].get("resident") is False
    # ③ 단지 필터(단지 이야기): complex 파라미터로 해당 단지 글만
    items = client.get("/community/posts", params={"complex": "청주더샵"}).json()["items"]
    assert items and all(p["complex_name"] == "청주더샵" for p in items)
    assert any(p["resident"] for p in items)


def test_edit_post_recomputes_resident_badge(client, db):
    """수정으로 @단지 태그를 바꾸면 주민 뱃지를 서버가 재산출 — 다른 단지로 편집해 뱃지를 옮기는 위조 차단."""
    from app.models import UserPref
    r = client.post("/auth/dev-login", json={"device_id": "dev-edit1", "nickname": "주민E"})
    tok = r.json().get("token") or r.json().get("access_token")
    h = {"Authorization": f"Bearer {tok}"}
    db.add(UserPref(device_id="dev-edit1",
                    data={"my_home": {"complex_name": "청주더샵", "lawd_cd": "43113"}}))
    db.commit()
    # 우리집 단지로 작성 → resident True
    pid = client.post("/community/posts", headers=h, json={
        "title": "우리 단지 이야기", "body": "본문입니다", "category": "free",
        "complex_name": "청주더샵", "lawd_cd": "43113"}).json()["post"]["id"]
    # 다른(주민 아님) 단지로 편집 → resident 는 False 로 재산출되어야 함(위조 차단)
    e = client.put(f"/community/posts/{pid}", headers=h, json={
        "complex_name": "남의아파트", "lawd_cd": "43111"})
    assert e.status_code == 200, e.text
    assert e.json()["post"].get("resident") is False
    # 다시 우리집 단지로 되돌리면 True 로 복구
    e2 = client.put(f"/community/posts/{pid}", headers=h, json={
        "complex_name": "청주더샵", "lawd_cd": "43113"})
    assert e2.json()["post"].get("resident") is True


def test_delete_comment_decrements_count_atomically(client, db):
    """댓글 삭제 시 comment_count 원자 감소(0 미만 방지)."""
    pid = _make_post(db)
    r = client.post("/auth/dev-login", json={"device_id": "dev-cmt", "nickname": "댓글러"})
    tok = r.json().get("token") or r.json().get("access_token")
    h = {"Authorization": f"Bearer {tok}"}
    c1 = client.post(f"/community/posts/{pid}/comments", headers=h, json={"body": "첫 댓글"}).json()["comment"]["id"]
    client.post(f"/community/posts/{pid}/comments", headers=h, json={"body": "둘째 댓글"})
    assert client.get(f"/community/posts/{pid}").json()["post"]["comment_count"] == 2
    client.delete(f"/community/comments/{c1}", headers=h)
    assert client.get(f"/community/posts/{pid}").json()["post"]["comment_count"] == 1
