"""SEO/공유 진입 페이지 — 순수 헬퍼 + 차별 신호(급매·전세위험) 노출(유입 후크·왜곡 없음).

오프라인 샌드박스는 fastapi 미설치로 import 불가 → CI/실서버 pytest에서 검증.
"""
from datetime import date
from app.api.landing import _eok, _page
from app.models import Transaction
from app.core import cache


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


def _trade(name, amt, key, lawd="43111", d=date(2026, 3, 1), floor=7, area=84.9):
    return Transaction(lawd_cd=lawd, property_type="apartment", deal_type="trade",
                       complex_name=name, exclusive_area=area, floor=floor,
                       contract_date=d, deal_amount=amt, source="TEST", dedup_key=key)


def _jeonse(name, dep, key, lawd="43111", d=date(2026, 5, 1)):
    return Transaction(lawd_cd=lawd, property_type="apartment", deal_type="jeonse",
                       complex_name=name, exclusive_area=84.9, contract_date=d,
                       deposit=dep, source="TEST", dedup_key=key)


def test_region_landing_shows_bargain_signal(client, db):
    for i, a in enumerate([50000, 51000, 52000, 53000]):
        db.add(_trade("랜딩단지", a, f"lb{i}"))
    db.add(_trade("랜딩단지", 40000, "llow", d=date(2026, 7, 1), floor=1))   # 중앙값 대비 크게 낮음(급매)
    db.commit()
    cache.bump_data_version()
    html = client.get("/r/43111").text
    assert "급매 감지" in html and "랜딩단지" in html
    assert "청집사 시그널" in html


def test_complex_landing_shows_jeonse_risk(client, db):
    for i, a in enumerate([50000, 52000, 54000]):
        db.add(_trade("전세단지", a, f"ct{i}", d=date(2026, 5, 1)))
    for i, dep in enumerate([46000, 47000, 48000]):
        db.add(_jeonse("전세단지", dep, f"cj{i}"))     # 전세가율 ~90% → 위험 표시
    db.commit()
    cache.bump_data_version()
    html = client.get("/c/43111/전세단지").text
    assert "전세가율 높음" in html


def test_guide_page_faq_and_links(client, db):
    h = client.get("/guide").text
    assert "청주 전입 가이드" in h
    assert "FAQPage" in h            # FAQ 리치결과 구조화 데이터
    assert 'href="/start"' in h      # 온보딩(창끝) 연결
    assert 'href="/r/43113"' in h    # 지역 내부 링크
    assert "중개·광고" in h            # 정체성 문구


def test_region_page_seo(client, db):
    for i, a in enumerate([50000, 51000, 52000]):
        db.add(_trade("에스이오단지", a, f"seo{i}"))
    db.commit(); cache.bump_data_version()
    h = client.get("/r/43111").text
    assert "BreadcrumbList" in h          # 브레드크럼 구조화
    assert "og:image" in h                # 공유 미리보기 이미지
    assert 'name="robots"' in h           # 색인 지시
    assert 'href="/r/43112"' in h         # 다른 구 내부 링크
    assert 'href="/guide"' in h           # 가이드 연결


def test_complex_page_not_orphan(client, db):
    from urllib.parse import quote
    for i, a in enumerate([50000, 51000, 52000]):
        db.add(_trade("대상단지", a, f"tg{i}"))
    for i, a in enumerate([40000, 41000, 42000]):
        db.add(_trade("이웃단지", a, f"nb{i}"))
    db.commit(); cache.bump_data_version()
    h = client.get(f"/c/43111/{quote('대상단지')}").text
    assert "BreadcrumbList" in h
    assert 'href="/r/43111"' in h         # 지역으로 돌아가는 링크(고립 해소)
    assert "다른 단지 시세" in h            # 같은 구 다른 단지 내부 링크


def test_sitemap_includes_guide(client, db):
    xml = client.get("/sitemap.xml").text
    assert "/guide" in xml


def test_onboarding_landing_picker(client, db):
    from app.models import CommuteDestination
    db.add(CommuteDestination(key="skhy", name="SK하이닉스 청주캠퍼스", category="job",
                              lat=36.675, lng=127.425, gu="흥덕구", is_active=True, sort_order=1))
    db.commit()
    html = client.get("/start").text
    assert "청주가 처음이세요" in html
    assert "SK하이닉스 청주캠퍼스" in html and "dest=skhy" in html
    assert "중개·광고 수익이 없" in html          # 정체성(말릴 수 있는 앱) 문구
    # 잘못된 dest → 픽커로 폴백
    assert "어디로 출근하세요" in client.get("/start?dest=없는거점").text
