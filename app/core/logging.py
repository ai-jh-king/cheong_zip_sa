"""로깅 설정 — 일관된 포맷 + 외부호출 소음 억제.

httpx/httpcore 의 요청 로그(매 외부 API 호출마다 INFO)가 운영 로그를 가리므로 WARNING 으로 낮춘다.
요청 타이밍 미들웨어(main)에서 메서드/경로/상태/지연을 한 줄로 남긴다.
"""
from __future__ import annotations
import logging

_CONFIGURED = False


def setup_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    lvl = getattr(logging, str(level).upper(), logging.INFO)
    root = logging.getLogger()
    if not _CONFIGURED:
        logging.basicConfig(
            level=lvl,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        _CONFIGURED = True
    root.setLevel(lvl)
    # 외부 HTTP 클라이언트 소음 억제(요청 URL 이 매번 INFO 로 찍히는 문제)
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
