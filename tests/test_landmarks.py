"""개발 호재(Landmark) — 주변 거리·전체·왜곡방지(status/출처 노출)."""
from app.models import Landmark
from app.services import landmarks as svc


def _lm(db, **kw):
    d = dict(name="호재", category="industry", status="confirmed",
             lat=36.64, lng=127.49, source_name="충북도", is_active=True)
    d.update(kw)
    l = Landmark(**d)
    db.add(l)
    db.commit()
    return l


def test_nearby_distance_and_labels(db):
    lat, lng = 36.6424, 127.489
    _lm(db, name="방사광가속기", lat=36.65, lng=127.50, status="ongoing",
        expected_year=2029, source_name="과기부", source_url="https://x")
    _lm(db, name="먼호재", lat=36.90, lng=127.90)             # 반경 밖
    out = svc.nearby(db, lat, lng, radius=4000)
    assert len(out) == 1
    assert out[0]["name"] == "방사광가속기"
    assert out[0]["status_label"] == "추진"                   # 왜곡방지: 단계 노출
    assert out[0]["category_label"] == "산업"
    assert out[0]["source_name"] == "과기부"
    assert out[0]["distance"] >= 0


def test_all_active_excludes_inactive(db):
    _lm(db, name="활성", is_active=True)
    _lm(db, name="비활성", is_active=False)
    names = [x["name"] for x in svc.all_active(db)]
    assert "활성" in names and "비활성" not in names


def test_nearby_none_without_coords(db):
    assert svc.nearby(db, None, None) is None
