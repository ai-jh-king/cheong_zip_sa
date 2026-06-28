"""회원 탈퇴(DELETE /auth/account) — cascade 삭제·익명화·확인필수·권한.

격리: conftest 가 AUTH_DEV_LOGIN=true + throwaway SQLite.
"""
from app.models import Account, Favorite, Listing, Post, DeviceLink


def _login(client, device_id="dev1", nickname="홍길동"):
    r = client.post("/auth/dev-login", json={"device_id": device_id, "nickname": nickname})
    assert r.status_code == 200
    return r.json()["token"], r.json()["account"]["id"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_delete_requires_auth(client):
    r = client.request("DELETE", "/auth/account", json={"confirm": True})
    assert r.status_code == 401


def test_delete_requires_confirm(client):
    token, _ = _login(client)
    r = client.request("DELETE", "/auth/account", headers=_auth(token), json={"confirm": False})
    assert r.status_code == 400


def test_delete_cascades_and_anonymizes(client, db):
    token, aid = _login(client, device_id="dev1", nickname="홍길동")
    # 개인 데이터 직접 생성(기기/계정 기준)
    db.add(Favorite(device_id="dev1", target_type="complex", target_id="t1"))
    db.add(Listing(device_id="dev1", title="내매물", deal_type="trade",
                   property_type="apartment", lawd_cd="43111", status="active"))
    db.add(Post(device_id="dev1", account_id=aid, nickname="홍길동",
                title="내 글", body="내용", category="free"))
    db.commit()

    r = client.request("DELETE", "/auth/account", headers=_auth(token), json={"confirm": True})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["deleted"]["favorites"] == 1
    assert body["deleted"]["listings"] == 1
    assert body["deleted"]["device_links"] == 1
    assert body["deleted"]["posts_anon"] == 1   # 게시글은 익명화(삭제 아님)

    db.expire_all()   # API가 별도 세션에서 커밋 → 테스트 세션 캐시 무효화 후 재조회
    # 계정·개인데이터 삭제 확인
    assert db.get(Account, aid) is None
    assert db.query(Favorite).filter_by(device_id="dev1").count() == 0
    assert db.query(Listing).filter_by(device_id="dev1").count() == 0
    assert db.query(DeviceLink).filter_by(account_id=aid).count() == 0
    # 게시글은 남되 작성자 식별 제거(스레드 보존)
    p = db.query(Post).filter_by(title="내 글").first()
    assert p is not None
    assert p.account_id is None and p.device_id is None
    assert p.nickname == "(탈퇴한 사용자)"


def test_token_invalid_after_delete(client):
    token, _ = _login(client, device_id="dev2")
    client.request("DELETE", "/auth/account", headers=_auth(token), json={"confirm": True})
    # 계정이 사라졌으므로 동일 토큰으로 /me 조회 시 401
    r = client.get("/auth/me", headers=_auth(token))
    assert r.status_code == 401
