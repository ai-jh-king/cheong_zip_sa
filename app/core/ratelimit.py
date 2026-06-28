"""인프로세스 레이트리미터(고정 윈도) — 어뷰징·스팸 1차 방어.

- 스레드 안전. 키별(버킷+클라이언트IP) 고정 윈도 카운터.
- 다중 워커/인스턴스에서는 프로세스별로 적용된다(전역 아님). 캐시와 동일한 트레이드오프로,
  더 엄격한 전역 제한이 필요하면 공유 저장소(Redis 등) 기반으로 교체 가능. (구조만 동일)
- 메모리: 키가 누적되지 않도록 주기적으로 만료 윈도 키를 정리(sweep).
"""
from __future__ import annotations
import threading
import time


class RateLimiter:
    def __init__(self) -> None:
        self._d: dict[str, list] = {}      # key -> [window_index, count]
        self._lock = threading.Lock()
        self._ops = 0

    def hit(self, key: str, limit: int, window_sec: int) -> tuple[bool, int]:
        """요청 1건 기록. (허용여부, 재시도까지 남은 초) 반환."""
        now = time.time()
        win = int(now // window_sec)
        with self._lock:
            self._ops += 1
            if self._ops % 5000 == 0:
                self._sweep(win)
            cur = self._d.get(key)
            if cur is None or cur[0] != win:
                self._d[key] = [win, 1]
                return True, 0
            if cur[1] >= limit:
                retry = int((win + 1) * window_sec - now) + 1
                return False, max(retry, 1)
            cur[1] += 1
            return True, 0

    def _sweep(self, win: int) -> None:
        stale = [k for k, v in self._d.items() if v[0] < win - 1]
        for k in stale:
            self._d.pop(k, None)


limiter = RateLimiter()
