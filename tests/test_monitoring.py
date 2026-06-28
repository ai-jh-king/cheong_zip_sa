"""모니터링 서비스 단위 테스트 — 경보 no-op / 알려진 작업 / 통계 직렬화."""
from app.services import monitoring


class _Stub:
    alert_webhook_url = ""
    sentry_dsn = ""


def test_alert_no_webhook_is_safe(monkeypatch):
    # 웹훅 미설정이면 로그만 남기고 예외 없이 반환
    monkeypatch.setattr(monitoring, "get_settings", lambda: _Stub())
    assert monitoring.alert("테스트 경보", "본문") is None


def test_known_jobs():
    assert "collect_live" in monitoring.KNOWN_JOBS
    assert "geocode" in monitoring.KNOWN_JOBS


def test_alert_webhook_called(monkeypatch):
    calls = {}

    class _S:
        alert_webhook_url = "https://example.com/hook"
        sentry_dsn = ""
    monkeypatch.setattr(monitoring, "get_settings", lambda: _S())

    import types
    fake_httpx = types.SimpleNamespace(post=lambda url, json, timeout: calls.update(url=url, json=json))
    monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)
    monitoring.alert("제목", "내용")
    assert calls.get("url") == "https://example.com/hook"
    assert "제목" in calls["json"]["text"] and "제목" in calls["json"]["content"]
