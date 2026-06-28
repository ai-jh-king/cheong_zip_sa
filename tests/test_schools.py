"""학군(통학 접근성) 요약 — 거리 최단·급별 분류·카운트."""
from app.api.complex import _school_summary


def test_school_summary_classifies_and_counts():
    schools = [
        {"name": "율량초등학교", "distance": 250},
        {"name": "청주중학교", "distance": 600},
        {"name": "운호고등학교", "distance": 1200},
        {"name": "어울림초등학교", "distance": 800},
    ]
    s = _school_summary(schools)
    assert s["count"] == 4
    assert s["nearest"]["distance"] == 250
    assert s["elementary"]["name"] == "율량초등학교"   # 가장 가까운 초등
    assert s["middle"]["name"] == "청주중학교"
    assert s["high"]["name"] == "운호고등학교"


def test_empty_schools_none():
    assert _school_summary([]) is None
