"""지오코딩 좌표 검증 — 구 경계 폴리곤 포함 검사(오좌표 자가치유 v1.236)."""
from app.services.geocode import _in_own_gu


def test_in_own_gu_inside():
    # 가경동(흥덕구 43113) 한복판
    assert _in_own_gu("43113", 36.6280, 127.4310) is True


def test_in_own_gu_outside():
    # 흥덕구 좌표를 상당구(43111)라고 주장 → False(오탐 검출)
    assert _in_own_gu("43111", 36.6280, 127.4310) is False


def test_in_own_gu_unknown_code_skips():
    assert _in_own_gu("99999", 36.6, 127.4) is None
