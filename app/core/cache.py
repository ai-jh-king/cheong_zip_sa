"""
인프로세스 TTL 캐시 — 외부 API 응답을 일정 시간 재사용.

목적: 대출·뉴스·청약 같은 외부 호출을 '매 요청'마다 하지 않도록(레이트리밋 보호·지연 감소).
특징:
  - TTL 만료 전이면 캐시값 반환(외부 호출 안 함).
  - single-flight: 같은 키를 동시에 여러 요청이 조회해도 외부 호출은 1회만(나머지는 대기 후 결과 공유).
  - negative caching: loader 가 None(실패/키없음)이면 짧게(neg_ttl)만 캐시 → 곧 재시도.
  - 스레드 안전(FastAPI 동기 엔드포인트는 스레드풀에서 동시 실행됨).

확장: 서버 여러 대로 가면 인프로세스 캐시는 서버별로 분리됨 → 공유가 필요하면 Redis 로 교체
      (get_or_set 인터페이스 유지). 현재 단계에선 서버당 외부호출을 크게 줄이는 1차 방어.
"""
from __future__ import annotations
import functools
import threading
import time

from app.core.config import get_settings


class TTLCache:
    def __init__(self) -> None:
        self._store: dict = {}          # key -> (value, expires_at)
        self._locks: dict = {}          # key -> Lock (single-flight)
        self._guard = threading.Lock()

    def _lock_for(self, key):
        with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._locks[key] = lock
            return lock

    def get_or_set(self, key, loader, ttl: int, neg_ttl: int = 60):
        now = time.time()
        ent = self._store.get(key)
        if ent and ent[1] > now:
            return ent[0]
        lock = self._lock_for(key)
        with lock:
            # 락 획득 후 재확인(다른 스레드가 이미 채웠을 수 있음)
            ent = self._store.get(key)
            now = time.time()
            if ent and ent[1] > now:
                return ent[0]
            value = loader()
            exp = now + (ttl if value is not None else neg_ttl)
            self._store[key] = (value, exp)
            return value

    def clear(self) -> None:
        with self._guard:
            self._store.clear()

    def stats(self) -> dict:
        now = time.time()
        live = sum(1 for _, exp in self._store.values() if exp > now)
        return {"entries": len(self._store), "live": live}


cache = TTLCache()


# ---------------- 데이터 버전 기반 집계 캐시 ----------------
# 수집(collect)/지오코딩으로 원천 데이터가 바뀌면 버전을 올려 즉시 무효화.
# 같은 버전 안에서는 '집계를 1회만 계산'하고 이후 요청은 캐시에서 제공
# (매 요청 전체 스캔+Python median 제거). 서버 여러 대면 서버당 1회 계산.
import copy as _copy

# 데이터 버전을 DB(app_meta)에 저장 → 수집이 '별도 컨테이너(cron)'에서 돌아도 그 bump가
# 웹 프로세스/다중 워커에 전파된다(인프로세스 int 였을 땐 크론 bump가 웹에 안 보여
# 캐시가 사실상 무효화되지 않았음 — TTL 만료로만 갱신되던 문제 해결).
# 매 stat 조회마다 DB를 때리지 않도록 로컬에 짧게(30초) 캐시 → bump는 최대 30초 내 전파.
_dv_guard = threading.Lock()
_dv_cache = {"v": None, "exp": 0.0}
_DV_KEY = "data_version"
_DV_LOCAL_TTL = 30


def _read_dv_from_db() -> int:
    from app.db.session import SessionLocal
    from app.services import appmeta
    with SessionLocal() as db:
        return appmeta.get_int(db, _DV_KEY, 0)


def get_data_version() -> int:
    now = time.time()
    with _dv_guard:
        if _dv_cache["v"] is not None and _dv_cache["exp"] > now:
            return _dv_cache["v"]
    try:
        v = _read_dv_from_db()
    except Exception:
        with _dv_guard:
            return _dv_cache["v"] if _dv_cache["v"] is not None else 0
    with _dv_guard:
        _dv_cache["v"] = v
        _dv_cache["exp"] = now + _DV_LOCAL_TTL
    return v


def bump_data_version() -> int:
    """원천 데이터 변경 후 호출 → 집계 캐시 무효화(신선도 보장). DB에 반영돼 프로세스 간 전파."""
    v = None
    try:
        from app.db.session import SessionLocal
        from app.services import appmeta
        with SessionLocal() as db:
            v = appmeta.get_int(db, _DV_KEY, 0) + 1
            appmeta.set(db, _DV_KEY, v)
    except Exception:
        with _dv_guard:                       # DB 불가 시 최소한 로컬 무효화는 유지
            v = (_dv_cache["v"] or 0) + 1
    with _dv_guard:
        _dv_cache["v"] = v
        _dv_cache["exp"] = time.time() + _DV_LOCAL_TTL
    return v


def stat_cached(default_ttl: int = 3600, ttl_attr: str = "cache_ttl_stats_sec"):
    """집계 함수 캐시 데코레이터.
    - 첫 인자 db(Session)는 캐시 키에서 제외(요청마다 달라지므로).
    - 키에 data_version 포함 → 수집/지오코딩 시 자동 무효화.
    - 반환값은 deepcopy → 호출부가 결과를 변형해도 캐시가 오염되지 않음.
    - TTL은 백스톱(버전 무효화가 1차, 만료가 2차)."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(db, *args, **kwargs):
            ttl = getattr(get_settings(), ttl_attr, default_ttl)
            key = ("stat", fn.__qualname__, get_data_version(), args,
                   tuple(sorted(kwargs.items())))
            val = cache.get_or_set(key, lambda: fn(db, *args, **kwargs), ttl)
            return _copy.deepcopy(val)
        return wrapper
    return deco


def ttl_cached(ttl_attr: str, default_ttl: int, neg_ttl: int = 60):
    """settings.<ttl_attr> 초 동안 함수 결과를 캐시. None 은 neg_ttl 만 캐시."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            ttl = getattr(get_settings(), ttl_attr, default_ttl)
            key = (fn.__module__ + "." + fn.__qualname__, args,
                   tuple(sorted(kwargs.items())))
            return cache.get_or_set(key, lambda: fn(*args, **kwargs), ttl, neg_ttl)
        return wrapper
    return deco
