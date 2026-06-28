"""공유·SEO 진입 페이지(서버 렌더링) — SPA(/)는 그대로, 발견·공유 통로만 추가.

- GET /r/{lawd_cd}            지역(구) 시세 요약 + OG 메타 + 앱 링크
- GET /c/{lawd_cd}/{name}     단지 시세 요약 + OG 메타 + 앱 링크
- GET /sitemap.xml           검색엔진 색인용(지역 + 주요 단지)
- GET /robots.txt            크롤링 허용 + sitemap 위치

목적: ① 구글 색인(검색 유입) ② 카카오톡/링크 공유 시 리치 미리보기(OG) ③ SPA 재작성 없이.
데이터 없으면 '수집 중' 안전 표기(왜곡 없음). 모든 동적 문자열은 html.escape.
"""
from __future__ import annotations
import html
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings
from app.data.region_codes import CHEONGJU_DISTRICTS
from app.services import stats

router = APIRouter(tags=["landing"])

_CODES = {d.code: d.name for d in CHEONGJU_DISTRICTS}   # '43113' -> '흥덕구'
SITE = "청주집사"


def _eok(manwon) -> str:
    if not manwon:
        return "—"
    return f"{manwon / 10000:.2f}억"


def _base(request: Request) -> str:
    s = get_settings()
    if s.public_base_url:
        return s.public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def _page(*, title: str, desc: str, url: str, body: str) -> HTMLResponse:
    t, d = html.escape(title), html.escape(desc)
    u = html.escape(url)
    doc = f"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{u}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{u}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<style>
:root{{--ink:#16242b;--muted:#5b6b73;--teal:#0F766E;--line:#e6ebec}}
*{{box-sizing:border-box}}body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;color:var(--ink);background:#f6f8f8}}
.wrap{{max-width:480px;margin:0 auto;padding:22px 18px 40px}}
.brand{{font-weight:800;color:var(--teal);font-size:14px}}
h1{{font-size:21px;margin:6px 0 2px}}.sub{{color:var(--muted);font-size:13px;margin-bottom:16px}}
.card{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px 16px;margin-bottom:12px}}
.big{{font-size:26px;font-weight:800}}.lbl{{color:var(--muted);font-size:12px}}
.row{{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end}}
.kv{{flex:1;min-width:90px}}.kv .v{{font-weight:800;font-size:16px}}
a.cta{{display:block;text-align:center;background:var(--teal);color:#fff;text-decoration:none;font-weight:800;padding:13px 0;border-radius:11px;margin-top:8px}}
a.item{{display:flex;justify-content:space-between;text-decoration:none;color:var(--ink);padding:10px 2px;border-top:1px solid var(--line)}}
a.item:first-child{{border-top:none}}.muted{{color:var(--muted);font-size:11px;line-height:1.6;margin-top:14px}}
</style></head><body><div class="wrap">
<div class="brand">🏠 {SITE} · 청주 실거래가</div>
{body}
<div class="muted">실거래 신고가는 지연·정정·해제가 있어 참고용입니다. 자료: 국토교통부 실거래가.</div>
</div></body></html>"""
    return HTMLResponse(doc)


@router.get("/r/{lawd_cd}", response_class=HTMLResponse)
def region_page(lawd_cd: str, request: Request, db: Session = Depends(get_db)):
    if lawd_cd not in _CODES:
        return _page(title=f"지역을 찾을 수 없습니다 | {SITE}", desc="청주 4개 구만 지원합니다.",
                     url=_base(request) + f"/r/{lawd_cd}",
                     body='<div class="card">청주 상당·서원·흥덕·청원구만 지원합니다.</div>'
                          '<a class="cta" href="/">청주집사 열기</a>')
    gu = _CODES[lawd_cd]
    ov = stats.price_overview(db, lawd_cd=lawd_cd, property_type="all", band="all")
    sm = ov.get("summary") or {}
    med, ratio, cnt = sm.get("median"), sm.get("ratio"), sm.get("count") or 0
    base = _base(request)
    url = f"{base}/r/{lawd_cd}"

    if med:
        desc = f"청주시 {gu} 평균 매매 {_eok(med)}" + (f", 전세가율 {ratio}%" if ratio else "") + f", 최근 거래 {cnt}건. 단지별 시세·추이를 한눈에."
        head = (f'<div class="card"><div class="lbl">청주시 {gu} · 평균 매매(중앙값)</div>'
                f'<div class="big">{_eok(med)}</div>'
                f'<div class="row" style="margin-top:10px">'
                f'<div class="kv"><div class="lbl">전세가율</div><div class="v">{ratio}%</div></div>'
                f'<div class="kv"><div class="lbl">최근 거래</div><div class="v">{cnt}건</div></div>'
                f'</div></div>')
    else:
        desc = f"청주시 {gu} 아파트·오피스텔·빌라 실거래가. 데이터 준비 중입니다."
        head = '<div class="card">아직 표시할 실거래가 없어요. 곧 업데이트됩니다.</div>'

    items = ""
    for c in (ov.get("complexes") or [])[:6]:
        nm = html.escape(c["name"])
        link = f'/c/{lawd_cd}/{quote(c["name"])}'
        items += (f'<a class="item" href="{link}"><span>{nm}</span>'
                  f'<span style="font-weight:800">{_eok(c["median"])} · {c["count"]}건</span></a>')
    body = (f'<h1>{gu} 아파트 시세·실거래가</h1>'
            f'<div class="sub">청주시 {gu} 매매·전세 실거래가 요약</div>'
            f'{head}')
    if items:
        body += f'<div class="card"><div class="lbl" style="margin-bottom:6px">주요 단지</div>{items}</div>'
    body += '<a class="cta" href="/">청주집사 앱에서 더 보기 →</a>'
    title = f"{gu} 아파트 시세·실거래가 | {SITE}"
    return _page(title=title, desc=desc, url=url, body=body)


@router.get("/c/{lawd_cd}/{name}", response_class=HTMLResponse)
def complex_page(lawd_cd: str, name: str, request: Request, db: Session = Depends(get_db)):
    base = _base(request)
    url = f"{base}/c/{lawd_cd}/{quote(name)}"
    if lawd_cd not in _CODES:
        return _page(title=f"단지를 찾을 수 없습니다 | {SITE}", desc="지역 코드를 확인하세요.",
                     url=url, body='<div class="card">잘못된 지역입니다.</div><a class="cta" href="/">청주집사 열기</a>')
    d = stats.complex_detail(db, name, lawd_cd, None)
    gu = (d.get("gu") or f"청주시 {_CODES[lawd_cd]}").replace("청주시 ", "")
    nm = html.escape(name)
    if not d.get("found"):
        desc = f"{gu} {name} 실거래가. 데이터 준비 중입니다."
        body = (f'<h1>{nm}</h1><div class="sub">{gu}</div>'
                '<div class="card">아직 표시할 실거래가 없어요. 곧 업데이트됩니다.</div>'
                '<a class="cta" href="/">청주집사 앱에서 보기 →</a>')
        return _page(title=f"{name} 시세 | {SITE}", desc=desc, url=url, body=body)

    med = d.get("median_amount")
    ratio = d.get("jeonse_ratio")
    cnt = d.get("trade_count") or 0
    by = d.get("build_year")
    desc = f"{gu} {name} 대표 매매 {_eok(med)}" + (f", 전세가율 {ratio}%" if ratio else "") + f", 최근 거래 {cnt}건."
    rows = f'<div class="kv"><div class="lbl">최근 거래</div><div class="v">{cnt}건</div></div>'
    if ratio:
        rows = f'<div class="kv"><div class="lbl">전세가율</div><div class="v">{ratio}%</div></div>' + rows
    if by:
        rows += f'<div class="kv"><div class="lbl">건축</div><div class="v">{by}년</div></div>'
    body = (f'<h1>{nm}</h1><div class="sub">{gu} · 대표 시세</div>'
            f'<div class="card"><div class="lbl">대표 매매(중앙값)</div>'
            f'<div class="big">{_eok(med)}</div>'
            f'<div class="row" style="margin-top:10px">{rows}</div></div>'
            f'<a class="cta" href="/">청주집사 앱에서 추이·상세 보기 →</a>')
    return _page(title=f"{name} 시세·실거래가 | {SITE}", desc=desc, url=url, body=body)


@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
def robots(request: Request):
    return f"User-agent: *\nAllow: /\nSitemap: {_base(request)}/sitemap.xml\n"


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap(request: Request, db: Session = Depends(get_db)):
    base = _base(request)
    urls = [f"{base}/"]
    for code in _CODES:
        urls.append(f"{base}/r/{code}")
        try:
            ov = stats.price_overview(db, lawd_cd=code, property_type="all", band="all")
            for c in (ov.get("complexes") or [])[:30]:
                urls.append(f"{base}/c/{code}/{quote(c['name'])}")
        except Exception:  # noqa
            pass
    body = "".join(f"<url><loc>{html.escape(u)}</loc></url>" for u in urls)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           f"{body}</urlset>")
    return Response(content=xml, media_type="application/xml")
