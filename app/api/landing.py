"""공유·SEO 진입 페이지(서버 렌더링) — SPA(/)는 그대로, 발견·공유 통로만 추가.

- GET /r/{lawd_cd}            지역(구) 시세 요약 + OG + 브레드크럼 + 내부링크
- GET /c/{lawd_cd}/{name}     단지 시세 요약 + OG + 브레드크럼 + 같은 구 단지 링크(고립 해소)
- GET /start                 전입자 온보딩 랜딩(창끝)
- GET /guide                 청주 전입 가이드(에버그린·공유용 + FAQ 리치결과)
- GET /sitemap.xml           검색엔진 색인용(지역 + 단지 최대 400/구 + lastmod)
- GET /robots.txt            크롤링 허용 + sitemap 위치

목적: ① 구글 색인(검색 유입) ② 카카오톡/링크 공유 시 리치 미리보기(OG+이미지) ③ SPA 재작성 없이.
SEO: 모든 페이지에 robots meta·canonical·og:image·JSON-LD(WebSite/Organization),
     /r·/c·/guide 에 BreadcrumbList, /guide 에 FAQPage. 내부 링크로 크롤 깊이·체류 확보.
데이터 없으면 '수집 중' 안전 표기(왜곡 없음). 모든 동적 문자열은 html.escape.
"""
from __future__ import annotations
import html
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings
from app.data.region_codes import CHEONGJU_DISTRICTS
from app.services import stats, pricecheck

router = APIRouter(tags=["landing"])

_CODES = {d.code: d.name for d in CHEONGJU_DISTRICTS}   # '43113' -> '흥덕구'
SITE = "청주집사"


def _eok(manwon) -> str:
    if not manwon:
        return "—"
    return f"{manwon / 10000:.2f}억"


def _gu_signals(db, lawd_cd: str):
    """이 구의 '말릴 수 있는' 신호(급매·전세위험) — 공유/색인 콘텐츠 후크용.
    경쟁 앱(중개·광고 수익)이 구조적으로 못 만드는 차별 콘텐츠. 데이터 없으면 빈 목록(왜곡 없음)."""
    try:
        bargains = [h for h in (pricecheck.bargain_radar(db, months=3, limit=40).get("items") or [])
                    if h.get("lawd_cd") == lawd_cd]
    except Exception:  # noqa
        bargains = []
    try:
        risks = [h for h in (pricecheck.jeonse_risk_map(db, min_ratio=80, limit=200).get("items") or [])
                 if h.get("lawd_cd") == lawd_cd]
    except Exception:  # noqa
        risks = []
    return bargains, risks


def _signal_card(bargains, risks) -> str:
    """급매·전세위험 신호 카드 HTML. 신호 없으면 빈 문자열."""
    if not (bargains or risks):
        return ""
    rows = ""
    if bargains:
        top = "".join(
            f'<a class="item" href="/c/{b["lawd_cd"]}/{quote(b["name"])}"><span>📉 {html.escape(b["name"])} '
            f'<span style="color:#5b6b73;font-size:12px">{b.get("pyeong","")}평</span></span>'
            f'<span style="font-weight:800;color:#1E5FC4">{b["diff_pct"]}%</span></a>'
            for b in bargains[:3])
        rows += (f'<div class="lbl" style="margin:2px 0 4px"><b style="color:#1E5FC4">📉 급매 감지 {len(bargains)}건</b> '
                 f'<span>· 같은 평형 중앙값보다 크게 낮은 실거래</span></div>{top}')
    if risks:
        top = "".join(
            f'<a class="item" href="/c/{r["lawd_cd"]}/{quote(r["name"])}"><span>⚠️ {html.escape(r["name"])}</span>'
            f'<span style="font-weight:800;color:#C77A1A">전세가율 {r["ratio"]}%</span></a>'
            for r in sorted(risks, key=lambda x: -x["ratio"])[:3])
        rows += (f'<div class="lbl" style="margin:12px 0 4px"><b style="color:#C77A1A">⚠️ 전세위험 {len(risks)}곳</b> '
                 f'<span>· 전세가율 높아 역전세 유의(단정 아님)</span></div>{top}')
    return (f'<div class="card"><div class="lbl" style="margin-bottom:6px;font-weight:800;color:var(--teal)">'
            f'청집사 시그널 <span style="font-weight:400">· 중개·광고 없이 데이터만</span></div>{rows}</div>')


def _base(request: Request) -> str:
    s = get_settings()
    if s.public_base_url:
        return s.public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def _jsonld(*nodes) -> str:
    """유효 노드들을 <script type=ld+json> 로. 검색엔진 이해·리치결과용(왜곡 없는 사실만)."""
    import json
    items = [n for n in nodes if n]
    if not items:
        return ""
    data = items[0] if len(items) == 1 else items
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'


def _website_node(origin: str) -> dict:
    return {"@context": "https://schema.org", "@type": "WebSite", "name": SITE,
            "url": origin + "/", "inLanguage": "ko-KR",
            "publisher": {"@type": "Organization", "name": SITE, "url": origin + "/"}}


def _breadcrumb(origin: str, crumbs):
    """crumbs=[(이름, 경로 or None)], 마지막=현재(링크 없음). (표시 HTML, JSON-LD 노드) 반환.
    내부 링크(크롤 깊이·체류)+검색 브레드크럼 리치결과 동시 확보."""
    parts, ld = [], []
    for i, (name, path) in enumerate(crumbs):
        ne = html.escape(name)
        if path:
            parts.append(f'<a href="{html.escape(path)}" style="color:var(--muted);text-decoration:none">{ne}</a>')
        else:
            parts.append(f'<span style="color:var(--ink)">{ne}</span>')
        ld.append({"@type": "ListItem", "position": i + 1, "name": name,
                   **({"item": origin + path} if path else {})})
    nav = ('<nav style="font-size:12px;color:var(--muted);margin:2px 0 10px">'
           + ' <span style="opacity:.5">›</span> '.join(parts) + '</nav>')
    node = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": ld}
    return nav, node


def _page(*, title: str, desc: str, url: str, body: str, jsonld=None) -> HTMLResponse:
    t, d = html.escape(title), html.escape(desc)
    u = html.escape(url)
    from urllib.parse import urlsplit
    o = urlsplit(url)
    origin = f"{o.scheme}://{o.netloc}" if o.scheme and o.netloc else ""
    img = html.escape(origin + "/icons/icon-512.png") if origin else ""
    nodes = ([_website_node(origin)] if origin else [])
    if jsonld:
        nodes += jsonld if isinstance(jsonld, list) else [jsonld]
    ld = _jsonld(*nodes)
    img_meta = (f'<meta property="og:image" content="{img}">'
                f'<meta property="og:image:width" content="512"><meta property="og:image:height" content="512">'
                f'<meta name="twitter:image" content="{img}">') if img else ""
    doc = f"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{u}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{u}">
{img_meta}
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
{ld}
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

    # 우리만의 차별 신호(급매·전세위험) — 공유 미리보기(OG) 앞머리에 세워 클릭 유도.
    bargains, risks = _gu_signals(db, lawd_cd)
    sig_card = _signal_card(bargains, risks)
    if bargains or risks:
        hook = []
        if bargains:
            hook.append(f"📉 급매 {len(bargains)}건")
        if risks:
            hook.append(f"⚠️ 전세위험 {len(risks)}곳")
        desc = " · ".join(hook) + " 감지 | " + desc

    items = ""
    for c in (ov.get("complexes") or [])[:6]:
        nm = html.escape(c["name"])
        link = f'/c/{lawd_cd}/{quote(c["name"])}'
        items += (f'<a class="item" href="{link}"><span>{nm}</span>'
                  f'<span style="font-weight:800">{_eok(c["median"])} · {c["count"]}건</span></a>')
    bc_html, bc_ld = _breadcrumb(base, [("청주 실거래가", "/"), (gu, None)])
    body = (bc_html
            + f'<h1>{gu} 아파트 시세·실거래가</h1>'
            f'<div class="sub">청주시 {gu} 매매·전세 실거래가 요약</div>'
            f'{head}{sig_card}')
    if items:
        body += f'<div class="card"><div class="lbl" style="margin-bottom:6px">주요 단지</div>{items}</div>'
    # 내부 링크: 다른 구 시세로(크롤 깊이·회유). + 전입 가이드.
    others = "".join(
        f'<a class="item" href="/r/{c}"><span>{html.escape(n)} 시세</span>'
        f'<span style="color:var(--teal);font-weight:800">›</span></a>'
        for c, n in _CODES.items() if c != lawd_cd)
    body += (f'<div class="card"><div class="lbl" style="margin-bottom:6px">청주 다른 구</div>{others}</div>'
             '<a class="item" href="/guide" style="border:none"><span>📖 청주 전입 가이드 — 동네·시세·조심할 점</span>'
             '<span style="color:var(--teal);font-weight:800">›</span></a>')
    body += '<a class="cta" href="/">청주집사 앱에서 더 보기 →</a>'
    title = f"{gu} 아파트 시세·실거래가 | {SITE}"
    return _page(title=title, desc=desc, url=url, body=body, jsonld=[bc_ld])


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
    # 이 단지 차별 신호(전세위험·급매) — 공유 미리보기(OG) 앞세워 후크. 판정 아님·면책은 하단 공통.
    badges = []
    if ratio and ratio >= 75:
        badges.append(("⚠️ 전세가율 높음", f"전세가율 {ratio}% · 역전세 유의(단정 아님)", "#C77A1A"))
    try:
        _bg = [b for b in (pricecheck.bargain_radar(db, months=3, limit=40).get("items") or [])
               if b.get("lawd_cd") == lawd_cd and b.get("name") == name]
    except Exception:  # noqa
        _bg = []
    if _bg:
        _best = min(_bg, key=lambda x: x["diff_pct"])
        badges.append(("📉 급매 감지", f"같은 평형 중앙값 대비 {_best['diff_pct']}% 실거래", "#1E5FC4"))
    sig_html = ""
    if badges:
        sig_html = '<div class="card">' + "".join(
            f'<div style="padding:5px 0"><b style="color:{c}">{t}</b> '
            f'<span class="lbl">{html.escape(sub)}</span></div>' for t, sub, c in badges) + '</div>'
        desc = " · ".join(t for t, _, _ in badges) + " · " + desc
    bc_html, bc_ld = _breadcrumb(base, [("청주 실거래가", "/"), (gu, f"/r/{lawd_cd}"), (name, None)])
    # 같은 구 다른 단지 — 내부 링크(고립 페이지 해소·크롤 깊이·회유)
    peers = ""
    try:
        ov = stats.price_overview(db, lawd_cd=lawd_cd, property_type="all", band="all")
        pl = [c for c in (ov.get("complexes") or []) if c.get("name") != name][:6]
        peers = "".join(
            f'<a class="item" href="/c/{lawd_cd}/{quote(c["name"])}"><span>{html.escape(c["name"])}</span>'
            f'<span style="font-weight:800">{_eok(c["median"])}</span></a>' for c in pl)
    except Exception:  # noqa
        peers = ""
    body = (bc_html
            + f'<h1>{nm}</h1><div class="sub">{gu} · 대표 시세</div>'
            f'<div class="card"><div class="lbl">대표 매매(중앙값)</div>'
            f'<div class="big">{_eok(med)}</div>'
            f'<div class="row" style="margin-top:10px">{rows}</div></div>'
            f'{sig_html}'
            f'<a class="cta" href="/">청주집사 앱에서 추이·상세 보기 →</a>')
    if peers:
        body += (f'<div class="card"><div class="lbl" style="margin-bottom:6px">{gu} 다른 단지 시세</div>{peers}</div>')
    body += (f'<a class="item" href="/r/{lawd_cd}" style="border:none"><span>📊 {gu} 전체 시세·실거래가</span>'
             '<span style="color:var(--teal);font-weight:800">›</span></a>')
    return _page(title=f"{name} 시세·실거래가 | {SITE}", desc=desc, url=url, body=body, jsonld=[bc_ld])


@router.get("/start", response_class=HTMLResponse)
def onboarding_landing(request: Request, dest: str = Query(""),
                       budget: int = Query(0, ge=0), db: Session = Depends(get_db)):
    """전입자 온보딩 공개 랜딩(설치 없이) — '창끝'. 직장 고르면 근처 단지+시세+예산 차액.
    SK하이닉스·오송·오창 발령자 단톡/카페에 뿌릴 공유용. 판정 없음·면책은 recommend notice."""
    from app.services import onboarding
    base = _base(request)
    opts = onboarding.options(db).get("destinations") or []
    keys = {o["key"] for o in opts}

    if not dest or dest not in keys:
        btns = "".join(
            f'<a class="item" href="/start?dest={o["key"]}"><span>🏭 {html.escape(o["name"])}'
            f'{" · " + html.escape(o["gu"]) if o.get("gu") else ""}</span>'
            f'<span style="color:var(--teal);font-weight:800">›</span></a>' for o in opts)
        picker = (f'<div class="card"><div class="lbl" style="margin-bottom:6px">어디로 출근하세요?</div>{btns}</div>'
                  if opts else '<div class="card">직장 거점 데이터 준비 중입니다. 곧 열립니다.</div>')
        body = ('<h1>청주가 처음이세요?</h1>'
                '<div class="sub">직장을 고르면 근처에 살 만한 단지를 <b>시세·조심할 점</b>까지 한눈에. 설치 없이.</div>'
                f'{picker}'
                '<div class="card" style="background:rgba(15,118,110,.06);border-color:rgba(15,118,110,.2)">'
                '💡 청집사는 <b>중개·광고 수익이 없어요.</b> 그래서 “이 단지 사세요”가 아니라 '
                '<b>조심할 점(급매·전세위험)</b>까지 솔직히 알려드릴 수 있어요.</div>'
                '<a class="cta" href="/">청집사 앱 열기 →</a>')
        desc = "청주 전입자 맞춤 — 직장 근처 살 만한 단지를 시세·조심할 점까지. 중개·광고 없이 데이터만 — 계약 전에 확인하세요."
        return _page(title="청주가 처음이세요? 직장 근처 단지 추천 | " + SITE,
                     desc=desc, url=base + "/start", body=body)

    rec = onboarding.recommend(db, dest, budget=(budget or None), limit=6)
    d = rec.get("destination") or {}
    dnm = html.escape(d.get("name") or "직장")
    items = rec.get("items") or []
    bform = (f'<form method="get" action="/start" class="card" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">'
             f'<input type="hidden" name="dest" value="{html.escape(dest)}">'
             f'<span class="lbl" style="flex:none">보유 현금(만원)</span>'
             f'<input name="budget" type="number" min="0" value="{budget or ""}" placeholder="예: 30000" '
             f'style="flex:1;min-width:120px;padding:9px;border:1px solid var(--line);border-radius:9px">'
             f'<button style="flex:none;background:var(--teal);color:#fff;border:none;border-radius:9px;padding:10px 16px;font-weight:800">적용</button></form>')
    cards = ""
    for it in items:
        price = _eok(it.get("latest_amount")) if it.get("latest_amount") else "—"
        over = it.get("over_budget_by")
        gap = ""
        if over is not None:
            gap = ('<span style="color:#1d7a4d;font-weight:800;font-size:12px">자기자본 이내</span>'
                   if over <= 0 else f'<span style="color:#5b6b73;font-size:12px">+{_eok(over)} 더 필요</span>')
        cards += (f'<a class="item" href="/c/{it["lawd_cd"]}/{quote(it["name"])}">'
                  f'<span>{html.escape(it["name"])} <span style="color:#5b6b73;font-size:12px">🚗 {it["minutes"]}분</span></span>'
                  f'<span style="text-align:right"><b>{price}</b><br>{gap}</span></a>')
    body = (f'<h1>{dnm} 근처 살 만한 단지</h1>'
            f'<div class="sub">직장에서 가깝고 시세를 확인한 단지예요. 예산을 넣으면 자기자본 대비 차액도.</div>'
            f'{bform}'
            + (f'<div class="card">{cards}</div>' if cards
               else '<div class="card">주변 단지 데이터가 준비 중입니다(실거래 수집·지오코딩 후 채워집니다).</div>')
            + f'<div class="muted">{html.escape(rec.get("notice") or "")}</div>'
            + '<a class="cta" href="/">청집사 앱에서 상세·추이 보기 →</a>')
    desc = f"{dnm} 근처 청주 아파트 — 통근시간·시세·예산 차액을 한눈에. 중개·광고 없이 데이터만, 조심할 점까지."
    return _page(title=f"{dnm} 근처 살 만한 단지 | " + SITE,
                 desc=desc, url=base + f"/start?dest={dest}", body=body)


# 구별 한 줄 소개(전입자용·사실 기반). 지역 페이지로 내부 링크.
_GU_BLURB = {
    "43111": "원도심·행정 중심(도청·법원). 생활 인프라 성숙, 구도심 재정비 이슈.",
    "43112": "충북대 등 대학가·주거지. 학군·정주 여건 선호.",
    "43113": "가경·복대 상권과 신흥 주거. SK하이닉스·테크노폴리스 인접(직주근접 수요).",
    "43114": "오창(산업단지·방사광가속기)·청주공항·북청주역세권. 개발 호재 밀집.",
}


@router.get("/guide", response_class=HTMLResponse)
def newcomer_guide(request: Request, db: Session = Depends(get_db)):
    """청주 전입 가이드(에버그린) — '창끝(전입자)' 공유용 + SEO 콘텐츠(내부링크·FAQ 리치결과).
    회사 단톡/HR 공유에 적합한 '설치 없는' 유용한 페이지. 중개·광고 0 정체성 반영."""
    base = _base(request)
    url = base + "/guide"
    bc_html, bc_ld = _breadcrumb(base, [("청주 실거래가", "/"), ("전입 가이드", None)])
    regions = "".join(
        f'<a class="item" href="/r/{c}"><span><b>{html.escape(n)}</b> '
        f'<span class="lbl">{html.escape(_GU_BLURB.get(c, ""))}</span></span>'
        f'<span style="color:var(--teal);font-weight:800">›</span></a>' for c, n in _CODES.items())
    faqs = [
        ("청주 어디에 살아야 하나요?",
         "정답은 직장 위치예요. 통근 거리 기준으로 후보 단지를 좁힌 뒤 시세와 조심할 점을 함께 보세요. "
         "청집사 ‘전입자 추천’에서 직장을 고르면 근처 단지를 시세·예산 차액과 함께 보여드려요."),
        ("전세가율이 높으면 위험한가요?",
         "전세가율(전세보증금÷매매가)이 높을수록 매매가 대비 보증금 비중이 커서, 시세가 내리면 보증금 회수가 "
         "어려워지는 역전세 위험이 커질 수 있어요. 단정은 아니고, 계약 전 등기부(선순위)와 함께 꼭 확인하세요."),
        ("급매면 무조건 좋은 건가요?",
         "같은 평형 중앙값보다 크게 낮은 실거래라도 직거래·가족 간 거래 등 특수 사유일 수 있어요. "
         "청집사는 이런 신호를 ‘사실’로만 보여주고 판정하지 않아요. 근거를 보고 판단하세요."),
    ]
    faq_html = "".join(
        f'<div style="padding:9px 0;border-top:1px solid var(--line)"><b>Q. {html.escape(q)}</b>'
        f'<div class="lbl" style="margin-top:4px;line-height:1.6">{html.escape(a)}</div></div>' for q, a in faqs)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q,
                              "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}
    body = (bc_html
            + '<h1>청주 전입 가이드</h1>'
            '<div class="sub">청주가 처음이신 분(SK하이닉스·오송·오창 발령 등)을 위한 동네·시세·조심할 점. '
            '중개·광고 없이 데이터만 — 계약 전에 확인하세요.</div>'
            '<div class="card"><div class="lbl" style="margin-bottom:6px">① 청주 4개 구, 한눈에</div>'
            f'{regions}</div>'
            '<div class="card" style="background:rgba(15,118,110,.06);border-color:rgba(15,118,110,.2)">'
            '<b>② 직장 근처부터 좁히세요</b><div class="lbl" style="margin-top:4px">직장을 고르면 근처 살 만한 '
            '단지를 시세·예산 차액까지 3분에.</div>'
            '<a class="cta" href="/start" style="margin-top:10px">전입자 맞춤 추천 받기 →</a></div>'
            '<div class="card"><div class="lbl" style="margin-bottom:6px">③ 조심할 점 (자주 묻는 질문)</div>'
            f'{faq_html}</div>'
            '<div class="card">💡 청집사는 <b>중개·광고 수익이 없어요.</b> 그래서 “여기 사세요”가 아니라 '
            '<b>급매·전세위험 같은 조심할 점</b>까지 솔직히 알려드릴 수 있어요. 계약 전 등기부·건축물대장 확인도 '
            '앱에 정리돼 있어요.</div>'
            '<a class="cta" href="/">청집사 앱 열기 →</a>')
    desc = ("청주 전입 가이드 — SK하이닉스·오송·오창 발령 등 청주가 처음인 분을 위한 동네·시세·조심할 점. "
            "중개·광고 없이 데이터만, 급매·전세위험까지 솔직히.")
    return _page(title="청주 전입 가이드 — 동네·시세·조심할 점 | " + SITE,
                 desc=desc, url=url, body=body, jsonld=[bc_ld, faq_ld])


_TIPS = [
    ("등기부등본은 내가 직접 뗀다",
     "인터넷등기소에서 700원. 계약 직전과 잔금 직전 두 번 확인하세요. 갑구(소유자)·을구(근저당)를 보고, 상대가 보여주는 서류가 아니라 내가 뗀 최신본을 기준으로 합니다."),
    ("소유자와 계약 상대가 같은지 확인",
     "등기부의 소유자와 신분증을 대조하고, 대리인 계약이면 위임장과 인감증명서를 확인합니다."),
    ("건축물대장 확인(정부24, 무료)",
     "위반건축물 여부와 실제 용도(주거용인지)를 확인합니다. 근린생활시설을 주택처럼 판매하는 사례가 있습니다."),
    ("호가가 아니라 실거래 신고가 기준",
     "부르는 값과 실제 거래가는 다릅니다. 국토부 실거래 공개시스템이나 청집사에서 단지별 실거래 중앙값을 확인하세요."),
    ("전세라면 전세가율 확인",
     "보증금÷매매시세. 청주 단지별로 60~80%대까지 제각각이며, 높을수록 시세 하락 시 보증금 회수 여력이 줄어듭니다."),
    ("보증금+선순위 채권을 시세와 비교",
     "근저당 있는 집이라면 (보증금+채권최고액)÷시세를 계산해 보세요. 청집사 '전세 안전 진단'이 공개 계산식으로 도와드립니다."),
    ("계약금은 등기부상 소유자 계좌로만",
     "다른 사람 계좌로 입금을 요구하면 진행을 멈추세요."),
    ("특약을 아까워하지 않기",
     "'잔금일까지 권리변동 없을 것', '보증보험 가입 불가 시 계약 해제' 등 구두 약속은 특약란에 적어야 분명해집니다."),
    ("전입신고+확정일자는 잔금 당일에",
     "전월세 보증금 보호(대항력·우선변제권)의 기본입니다. 주민센터 또는 정부24에서 바로 처리하세요."),
    ("관리비·세금까지 월 부담으로 계산",
     "관리비·재산세·대출이자를 합쳐 월 기준으로 보면 부담을 과소평가하지 않습니다."),
]


@router.get("/tips", response_class=HTMLResponse)
def tips_page(request: Request):
    """부동산 거래 주의점 10가지 — 일반 유입용 에버그린 랜딩(검색·공유).
    제도 사실만(왜곡 없음), FAQ 리치결과(JSON-LD), 앱·도감 CTA."""
    base = _base(request)
    url = base + "/tips"
    bc_html, bc_ld = _breadcrumb(base, [("청주 실거래가", "/"), ("거래 전 확인 10가지", None)])
    items = "".join(
        f'<div style="padding:11px 0;border-top:1px solid var(--line)"><b>{i+1}. {html.escape(t)}</b>'
        f'<div class="lbl" style="margin-top:4px;line-height:1.65">{html.escape(a)}</div></div>'
        for i, (t, a) in enumerate(_TIPS))
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": t,
                              "acceptedAnswer": {"@type": "Answer", "text": a}} for t, a in _TIPS]}
    body = (bc_html
            + '<h1>부동산 거래가 처음이라면 — 계약 전 확인 10가지</h1>'
            '<div class="sub">매매·전월세 공통. 전부 제도적으로 확인 가능한 사실만 모았습니다.</div>'
            f'<div class="card">{items}</div>'
            '<div class="card" style="background:rgba(15,118,110,.06);border-color:rgba(15,118,110,.2)">'
            '💡 청집사는 <b>중개·광고 수익이 없어</b> 계약을 부추길 이유도, 말릴 이유도 없습니다. '
            '그래서 이런 목록을 그대로 드릴 수 있어요. 앱에는 전세 안전 진단 계산기와 공식 사이트 링크 모음이 있습니다.</div>'
            '<a class="cta" href="/">청집사 앱에서 실거래·안전 진단 보기 →</a>'
            '<a class="item" href="/guide" style="border:none;margin-top:6px"><span>📖 청주 전입 가이드</span>'
            '<span style="color:var(--teal);font-weight:800">›</span></a>')
    desc = "부동산 계약 전 확인 10가지 — 등기부·건축물대장·전세가율·특약·확정일자. 매매·전월세 공통, 제도 사실만. 중개·광고 없는 청집사."
    return _page(title="부동산 계약 전 확인 10가지 (매매·전월세 공통) | " + SITE,
                 desc=desc, url=url, body=body, jsonld=[bc_ld, faq_ld])


@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
def robots(request: Request):
    return f"User-agent: *\nAllow: /\nSitemap: {_base(request)}/sitemap.xml\n"


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap(request: Request, db: Session = Depends(get_db)):
    base = _base(request)
    # lastmod = 마지막 수집 날짜(데이터 신선도) — 크롤러 재방문 힌트.
    try:
        from app.services import appmeta
        at = ((appmeta.get_json(db, "last_collect") or {}).get("at") or "")[:10]
    except Exception:  # noqa
        at = ""
    lastmod = at if len(at) == 10 else ""
    urls = [f"{base}/", f"{base}/start", f"{base}/guide", f"{base}/tips"]
    for code in _CODES:
        urls.append(f"{base}/r/{code}")
        try:
            ov = stats.price_overview(db, lawd_cd=code, property_type="all", band="all")
            for c in (ov.get("complexes") or [])[:400]:   # 단지 색인 커버리지 확대(구당 최대 400)
                urls.append(f"{base}/c/{code}/{quote(c['name'])}")
        except Exception:  # noqa
            pass
    lm = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
    body = "".join(f"<url><loc>{html.escape(u)}</loc>{lm}</url>" for u in urls)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           f"{body}</urlset>")
    return Response(content=xml, media_type="application/xml")
