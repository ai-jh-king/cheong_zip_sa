"""레이트리미터(고정 윈도) 단위 — 한도 내 허용, 초과 시 차단, 키 분리."""
from app.core.ratelimit import RateLimiter


def test_allows_up_to_limit_then_blocks():
    rl = RateLimiter()
    ok = [rl.hit("k", 3, 60)[0] for _ in range(3)]
    assert ok == [True, True, True]
    allowed, retry = rl.hit("k", 3, 60)
    assert allowed is False
    assert retry >= 1            # Retry-After 초


def test_separate_keys_independent():
    rl = RateLimiter()
    assert rl.hit("a", 1, 60)[0] is True
    assert rl.hit("a", 1, 60)[0] is False   # a 소진
    assert rl.hit("b", 1, 60)[0] is True     # b 는 독립


def test_window_reset(monkeypatch):
    import app.core.ratelimit as m
    t = {"now": 1000.0}
    monkeypatch.setattr(m.time, "time", lambda: t["now"])
    rl = m.RateLimiter()
    assert rl.hit("k", 1, 60)[0] is True
    assert rl.hit("k", 1, 60)[0] is False
    t["now"] += 61                          # 다음 윈도로 이동
    assert rl.hit("k", 1, 60)[0] is True     # 리셋되어 다시 허용
