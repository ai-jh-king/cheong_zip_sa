"""세션 토큰/상태 서명 — 외부 의존성 없이 stdlib HMAC-SHA256(JWT 호환 HS256).

- make_token/read_token: 로그인 세션(Bearer) 토큰.
- sign_state/read_state: OAuth CSRF 방지 + device_id 운반용 state(짧은 만료).
배포 시 JWT_SECRET 를 .env 로 반드시 설정한다(미설정 시 프로세스 임시 키 → 재시작 시 로그아웃).
"""
import base64
import hashlib
import hmac
import json
import secrets
import time

from app.core.config import get_settings

_EPHEMERAL = secrets.token_urlsafe(32)


def _secret() -> str:
    s = get_settings()
    return s.jwt_secret or _EPHEMERAL


def _b64(b: bytes) -> bytes:
    return base64.urlsafe_b64encode(b).rstrip(b"=")


def _ub64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _encode(payload: dict, secret: str) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signing = header + b"." + body
    sig = hmac.new(secret.encode(), signing, hashlib.sha256).digest()
    return (signing + b"." + _b64(sig)).decode()


def _decode(token: str, secret: str) -> dict | None:
    try:
        header, body, sig = token.split(".")
        signing = (header + "." + body).encode()
        expected = _b64(hmac.new(secret.encode(), signing, hashlib.sha256).digest()).decode()
        if not hmac.compare_digest(expected, sig):
            return None
        payload = json.loads(_ub64(body))
        if payload.get("exp") and payload["exp"] < time.time():
            return None
        return payload
    except Exception:
        return None


def make_token(account_id: int, role: str, nick: str | None, provider: str, days: int | None = None) -> str:
    s = get_settings()
    days = days or s.session_days
    now = int(time.time())
    return _encode({"sub": str(account_id), "role": role, "nick": nick or "",
                    "prov": provider, "iat": now, "exp": now + days * 86400}, _secret())


def read_token(token: str) -> dict | None:
    return _decode(token, _secret())


def sign_state(data: str) -> str:
    return _encode({"d": data, "exp": int(time.time()) + 600}, _secret())


def read_state(token: str) -> str | None:
    p = _decode(token, _secret())
    return p.get("d") if p else None
