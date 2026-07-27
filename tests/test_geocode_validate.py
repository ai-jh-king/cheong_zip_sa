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


def test_payload_addresses_road_and_jibun():
    from app.services.geocode import _payload_addresses
    d = {"roadNm": "산성로116번길", "roadNmBonbun": "00023", "roadNmBubun": "00000", "jibun": "418"}
    road, jib = _payload_addresses(d, "청주시 상당구", "용담동")
    assert road == "충청북도 청주시 상당구 산성로116번길 23"
    assert jib == "충청북도 청주시 상당구 용담동 418"


def test_payload_addresses_bubun_and_missing():
    from app.services.geocode import _payload_addresses
    d = {"roadNm": "수영로", "roadNmBonbun": "00180", "roadNmBubun": "00002"}
    road, jib = _payload_addresses(d, "청주시 상당구", None)
    assert road == "충청북도 청주시 상당구 수영로 180-2"
    assert jib is None            # 지번·동 없으면 만들지 않음(추측 금지)
    assert _payload_addresses({}, "청주시 상당구", "용담동") == (None, None)
