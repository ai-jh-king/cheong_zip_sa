"""생활·교육·운동 시설(Place) — 분류·반경조회·지역요약."""
from app.models import Place
from app.services import places as svc


def _place(db, **kw):
    d = dict(name="X", category="education", subcategory="academy_exam",
             source="public", lat=36.64, lng=127.49)
    d.update(kw)
    d.setdefault("source_key", d["name"])
    p = Place(**d)
    db.add(p)
    db.commit()
    return p


def test_classify_academy():
    assert svc.classify_academy("외국어", "영어회화") == "academy_lang"
    assert svc.classify_academy("예능", "태권도") == "academy_pe"
    assert svc.classify_academy(None, "피아노") == "academy_art"
    assert svc.classify_academy("입시", "수학") == "academy_exam"
    assert svc.classify_academy("컴퓨터", "코딩") == "academy_it"
    assert svc.classify_academy("", "") == "academy_etc"


def test_nearby_distance_and_buckets(db):
    lat, lng = 36.6424, 127.489
    _place(db, name="가까운영어", subcategory="academy_lang", lat=36.6430, lng=127.4895, source_key="a1")
    _place(db, name="가까운태권도", subcategory="academy_pe", lat=36.6420, lng=127.4885, source_key="a2")
    _place(db, name="먼학원", subcategory="academy_exam", lat=36.70, lng=127.55, source_key="a3")     # 반경 밖
    _place(db, name="좌표없음", subcategory="library", lat=None, lng=None, source_key="a4")            # 제외
    out = svc.nearby(db, lat, lng, radius=1200)
    assert "academy_lang" in out and "academy_pe" in out
    assert "academy_exam" not in out                      # 너무 멀어 제외(왜곡 방지)
    assert out["academy_lang"]["items"][0]["name"] == "가까운영어"
    assert out["academy_lang"]["label"] == "외국어"


def test_nearby_none_without_coords(db):
    assert svc.nearby(db, None, None) is None              # 기준 좌표 없으면 None


def test_by_region_counts(db):
    _place(db, name="A", lawd_cd="43111", subcategory="academy_exam", source_key="r1")
    _place(db, name="B", lawd_cd="43111", subcategory="academy_exam", source_key="r2")
    _place(db, name="C", lawd_cd="43111", subcategory="library", source_key="r3")
    out = svc.by_region(db, "43111")
    assert out["academy_exam"]["count"] == 2
    assert out["library"]["count"] == 1


def test_fit_score_basic(db):
    """가족 맞춤 점수 — 가중치 준 항목만 반영, 데이터 없는 항목은 score None."""
    lat, lng = 36.6424, 127.489
    _place(db, name="가까운영어", subcategory="academy_lang", lat=36.6430, lng=127.4895, source_key="f1")
    _place(db, name="태권도", subcategory="academy_pe", lat=36.6428, lng=127.4892, source_key="f2")
    _place(db, name="헬스장", subcategory="sports", lat=36.6420, lng=127.4885, source_key="f3")
    # 학원·운동 중요, 도서관도 원하지만 데이터 없음
    out = svc.fit_score(db, lat, lng, {"academy": 5, "sports": 3, "library": 4}, radius=1500)
    assert out["overall"] is not None and 0 <= out["overall"] <= 100
    assert out["categories"]["academy"]["count"] >= 1
    assert out["categories"]["academy"]["score"] is not None
    assert out["categories"]["library"]["score"] is None          # 데이터 없음 → 점수 안 지어냄
    assert out["categories"]["library"].get("note") == "데이터 없음"
    assert "medical" not in out["categories"]                     # 가중치 0 → 제외


def test_fit_score_no_coords(db):
    assert svc.fit_score(db, None, None, {"academy": 5})["overall"] is None


def test_in_bounds_bbox_and_category(db):
    """지도 POI: bbox 안의 시설만, 카테고리 필터 반영. 데이터 없으면 빈 리스트."""
    _place(db, name="상당학원", category="education", subcategory="academy_exam",
           lat=36.64, lng=127.49, source_key="b1")
    _place(db, name="흥덕체육관", category="sports", subcategory="sports",
           lat=36.64, lng=127.42, source_key="b2")
    _place(db, name="범위밖학원", category="education", subcategory="academy_exam",
           lat=37.50, lng=127.00, source_key="b3")   # 서울권(범위 밖)
    # 청주 대략 bbox
    res = svc.in_bounds(db, 36.55, 36.75, 127.30, 127.55)
    names = {p["name"] for p in res["places"]}
    assert "상당학원" in names and "흥덕체육관" in names
    assert "범위밖학원" not in names                      # bbox 밖 제외
    # 카테고리 필터
    edu = svc.in_bounds(db, 36.55, 36.75, 127.30, 127.55, groups=["education"])
    edu_names = {p["name"] for p in edu["places"]}
    assert "상당학원" in edu_names and "흥덕체육관" not in edu_names
    # 좌표 없는 시설은 지도에 안 뜸
    _place(db, name="좌표없는곳", category="living", subcategory="library",
           lat=None, lng=None, source_key="b4")
    res2 = svc.in_bounds(db, 36.55, 36.75, 127.30, 127.55)
    assert "좌표없는곳" not in {p["name"] for p in res2["places"]}


def test_geocode_places_requires_key(db, monkeypatch):
    """지오코딩 키가 하나도 없으면 GeocodeKeyMissing(안전 실패, 왜곡 없음)."""
    from app.services import geocode as g
    from app.core.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "kakao_rest_api_key", "", raising=False)
    monkeypatch.setattr(s, "geocode_use_naver", False, raising=False)
    import pytest
    with pytest.raises(g.GeocodeKeyMissing):
        g.run_geocode_places(db)
