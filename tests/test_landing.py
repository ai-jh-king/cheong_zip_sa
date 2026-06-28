"""SEO/공유 진입 페이지 — 순수 헬퍼 테스트(서버/CI에서 실행).

오프라인 샌드박스는 fastapi 미설치로 import 불가 → CI/실서버 pytest에서 검증.
"""
from app.api.landing import _eok, _page


def test_eok_format():
    assert _eok(31920) == "3.19억"
    assert _eok(None) == "—"
    assert _eok(0) == "—"


def test_page_has_og_and_escapes():
    r = _page(title="흥덕구 시세 | 청주집사", desc="평균 3.19억",
              url="https://x/r/43113", body="<h1>x</h1>")
    body = r.body.decode() if hasattr(r, "body") else str(r)
    assert 'property="og:title"' in body
    assert 'property="og:description"' in body
    assert 'property="og:url"' in body
    assert "<title>" in body


def test_page_escapes_title():
    r = _page(title="<script>bad</script>", desc="d", url="u", body="b")
    body = r.body.decode()
    assert "<script>bad" not in body and "&lt;script&gt;" in body
