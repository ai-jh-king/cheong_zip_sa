"""웹푸시 서비스 단위 테스트 — VAPID 키 없으면 발송하지 않음(no-op)."""
from app.services import push


class _Stub:
    def __init__(self, pub="", priv=""):
        self.vapid_public_key = pub
        self.vapid_private_key = priv
        self.vapid_subject = "mailto:x@y.z"

    @property
    def push_enabled(self):
        return bool(self.vapid_public_key and self.vapid_private_key)


def test_disabled_when_no_keys(monkeypatch):
    monkeypatch.setattr(push, "get_settings", lambda: _Stub("", ""))
    assert push.is_enabled() is False
    assert push.public_key() is None
    # 비활성 상태에선 db/구독을 건드리지 않고 즉시 no-op
    res = push.dispatch(None, [], {"title": "t", "body": "b"})
    assert res["sent"] == 0 and res["enabled"] is False


def test_enabled_flag_and_public_key(monkeypatch):
    monkeypatch.setattr(push, "get_settings", lambda: _Stub("PUBKEY", "PRIVKEY"))
    assert push.is_enabled() is True
    assert push.public_key() == "PUBKEY"
    # 활성이어도 구독이 없으면 발송 0 (db 접근 없음)
    res = push.dispatch(None, [], {"title": "t"})
    assert res["sent"] == 0 and res["skipped"] == 0
