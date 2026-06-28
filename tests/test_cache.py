"""데이터 버전 기반 집계 캐시(stat_cached) 동작."""
from app.core import cache


def test_memoizes_then_invalidates_on_version_bump():
    calls = {"n": 0}

    @cache.stat_cached(default_ttl=60)
    def agg(db, x):
        calls["n"] += 1
        return {"x": x}

    assert agg(None, 1) == {"x": 1}
    assert agg(None, 1) == {"x": 1}
    assert calls["n"] == 1            # 두 번째는 캐시 적중

    cache.bump_data_version()
    assert agg(None, 1) == {"x": 1}
    assert calls["n"] == 2            # 버전 올라가면 재계산


def test_deepcopy_prevents_cache_pollution():
    @cache.stat_cached(default_ttl=60)
    def agg(db):
        return {"items": [1, 2, 3]}

    a = agg(None)
    a["items"].append(99)            # 호출부에서 변형
    assert agg(None)["items"] == [1, 2, 3]   # 캐시는 오염되지 않음
