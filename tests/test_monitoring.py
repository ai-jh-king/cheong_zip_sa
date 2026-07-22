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


def test_appmeta_set_caps_long_value(db):
    """app_meta.value=String(200). 긴 값이 와도 크래시 없이 잘라 저장(실사고: pg_dump 실패 기록 시
    StringDataRightTruncation 으로 배치 크래시)."""
    from app.services import appmeta
    appmeta.set(db, "last_backup", "x" * 500)
    assert len(appmeta.get(db, "last_backup")) <= 200


def test_record_job_fail_status_fits_column(db):
    """긴 예외로 실패해도 last_backup 상태 기록이 크래시하지 않고 유효 JSON 으로 남는다."""
    from app.services import monitoring, appmeta
    long_err = "pg_dump 실패: " + "server version mismatch " * 20
    try:
        monitoring.record_job(db, "backup", lambda: (_ for _ in ()).throw(RuntimeError(long_err)))
    except RuntimeError:
        pass
    st = appmeta.get_json(db, "last_backup")
    assert st and st.get("status") == "fail"        # 유효 JSON 으로 파싱됨(잘려도 깨지지 않음)


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
