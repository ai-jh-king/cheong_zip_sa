"""운영용 관리자 API — 권한 보호(토큰).

- 지오코딩/수집을 서버에서 트리거(백그라운드) + 좌표 커버리지 상태 조회.
- 보호: ADMIN_TOKEN 헤더(X-Admin-Token). 토큰 미설정 시 전체 비활성(403).
- 동시 실행 방지(in-process 플래그). 장시간 작업은 백그라운드 처리.
- 간단한 관리자 UI(/admin/ui) 제공 — 토큰은 클라이언트에서 입력(서버 저장 안 함).
"""
import hmac
import threading

from fastapi import APIRouter, Depends, Header, HTTPException, BackgroundTasks, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, distinct
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db, SessionLocal
from app.models import Complex, Transaction

router = APIRouter(prefix="/admin", tags=["admin"])

_lock = threading.Lock()
_state = {"running": False, "last": None}


def _require_admin(x_admin_token: str | None):
    s = get_settings()
    if not s.admin_token:
        raise HTTPException(status_code=403, detail="관리자 API가 비활성화되어 있습니다(ADMIN_TOKEN 미설정).")
    if not (x_admin_token and hmac.compare_digest(x_admin_token, s.admin_token)):
        raise HTTPException(status_code=401, detail="관리자 토큰이 올바르지 않습니다.")   # 타이밍-세이프 비교


def _coverage(db: Session) -> dict:
    distinct_complexes = db.scalar(
        select(func.count()).select_from(
            select(Transaction.complex_name, Transaction.lawd_cd)
            .where(Transaction.complex_name.isnot(None)).distinct().subquery()
        )
    ) or 0
    complex_rows = db.scalar(select(func.count()).select_from(Complex)) or 0
    geocoded = db.scalar(select(func.count()).select_from(Complex).where(Complex.lat.isnot(None))) or 0
    pct = round(geocoded / distinct_complexes * 100, 1) if distinct_complexes else None
    return {"distinct_complexes": distinct_complexes, "complex_rows": complex_rows,
            "geocoded": geocoded, "missing": max(distinct_complexes - geocoded, 0),
            "coverage_pct": pct}


@router.get("/status")
def status(db: Session = Depends(get_db), x_admin_token: str | None = Header(None)):
    _require_admin(x_admin_token)
    return {"job": _state, **_coverage(db)}


@router.get("/monitor")
def monitor(db: Session = Depends(get_db), x_admin_token: str | None = Header(None)):
    """모니터링 통합 상태 — DB·데이터 신선도·최근 실행·카운트·경고."""
    _require_admin(x_admin_token)
    from app.services.monitoring import system_status
    return system_status(db)


@router.get("/runs")
def runs(db: Session = Depends(get_db), x_admin_token: str | None = Header(None),
         limit: int = Query(20, ge=1, le=100), name: str | None = Query(None)):
    """배치 실행 이력(수집/지오코딩 등)."""
    _require_admin(x_admin_token)
    from app.services.monitoring import recent_runs
    return {"items": recent_runs(db, limit=limit, name=name)}


def _run_geocode_job(limit: int | None):
    if not _lock.acquire(blocking=False):
        return
    try:
        _state["running"] = True
        from app.services.geocode import run_geocode
        with SessionLocal() as db:
            res = run_geocode(db, limit=limit)
        _state["last"] = {"task": "geocode", **res}
    except Exception as e:  # noqa
        _state["last"] = {"task": "geocode", "error": str(e)}
    finally:
        _state["running"] = False
        _lock.release()


def _run_collect_job(months: int | None, then_geocode: bool):
    if not _lock.acquire(blocking=False):
        return
    try:
        _state["running"] = True
        from app.pipeline.collect import collect_live
        from app.services.geocode import run_geocode
        with SessionLocal() as db:
            res = collect_live(db) if months is None else collect_live(db, months_back=months)
            out = {"task": "collect", **(res if isinstance(res, dict) else {"result": str(res)})}
            if then_geocode:
                g = run_geocode(db)
                out["geocode"] = g
        _state["last"] = out
    except Exception as e:  # noqa
        _state["last"] = {"task": "collect", "error": str(e)}
    finally:
        _state["running"] = False
        _lock.release()


@router.post("/geocode")
def trigger_geocode(bg: BackgroundTasks, limit: int = Query(0, description="0=전체"),
                    x_admin_token: str | None = Header(None)):
    _require_admin(x_admin_token)
    if _state["running"]:
        raise HTTPException(status_code=409, detail="이미 작업이 실행 중입니다.")
    bg.add_task(_run_geocode_job, (limit or None))
    return {"started": True, "task": "geocode", "limit": limit or None}


@router.post("/collect")
def trigger_collect(bg: BackgroundTasks, months: int = Query(0, description="0=기본 개월수"),
                    geocode: bool = Query(True, description="수집 후 지오코딩 여부"),
                    x_admin_token: str | None = Header(None)):
    _require_admin(x_admin_token)
    if _state["running"]:
        raise HTTPException(status_code=409, detail="이미 작업이 실행 중입니다.")
    bg.add_task(_run_collect_job, (months or None), geocode)
    return {"started": True, "task": "collect", "months": months or None, "geocode": geocode}


def _run_enrich_job(limit: int | None):
    from app.services.enrich import enrich_complexes, EnrichDisabled
    with SessionLocal() as db:
        try:
            _state["running"] = True
            res = enrich_complexes(db, limit=limit)
            _state["last"] = {"task": "enrich", **res}
        except EnrichDisabled as e:
            _state["last"] = {"task": "enrich", "skipped": str(e)}
        except Exception as e:  # noqa
            _state["last"] = {"task": "enrich", "error": str(e)}
        finally:
            _state["running"] = False


@router.post("/enrich")
def trigger_enrich(bg: BackgroundTasks, limit: int = Query(0, description="0=전체"),
                   x_admin_token: str | None = Header(None)):
    """단지 기본정보 보강(K-apt). KAPT URL 미설정 시 건너뜀."""
    _require_admin(x_admin_token)
    if _state["running"]:
        raise HTTPException(status_code=409, detail="이미 작업이 실행 중입니다.")
    bg.add_task(_run_enrich_job, (limit or None))
    return {"started": True, "task": "enrich", "limit": limit or None}


@router.post("/test/sponsor")
def test_set_sponsor(listing_id: int = Query(...), on: bool = Query(True), priority: int = Query(0),
                     db: Session = Depends(get_db), x_admin_token: str | None = Header(None)):
    """[테스트용] 매물 광고/제휴 노출 토글. feature_ads ON일 때만 목록 정렬에 반영(OFF면 저장만 되고 노출 영향 없음)."""
    _require_admin(x_admin_token)
    from app.models import Listing
    row = db.get(Listing, listing_id)
    if not row:
        raise HTTPException(status_code=404, detail="매물을 찾을 수 없습니다.")
    row.is_sponsored = bool(on)
    row.priority = int(priority)
    db.commit()
    return {"id": row.id, "is_sponsored": row.is_sponsored, "priority": row.priority,
            "feature_ads": get_settings().feature_ads}


@router.post("/test/plan")
def test_set_plan(account_id: int = Query(...), plan: str = Query("premium"),
                  db: Session = Depends(get_db), x_admin_token: str | None = Header(None)):
    """[테스트용] 계정 plan 설정(free|premium). feature_monetization ON일 때만 is_premium 에 반영."""
    _require_admin(x_admin_token)
    from app.models import Account
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다.")
    acc.plan = plan if plan in ("free", "premium") else "free"
    db.commit()
    return {"id": acc.id, "plan": acc.plan, "feature_monetization": get_settings().feature_monetization}


@router.get("/ui", response_class=HTMLResponse)
def admin_ui():
    # 토큰은 입력창에서 받아 헤더로만 전송(서버 저장/노출 없음).
    return """<!doctype html><html lang=ko><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>청주 시세 · 관리자</title>
<style>body{font-family:system-ui,Pretendard,sans-serif;max-width:560px;margin:0 auto;padding:18px;color:#1b2b2b;background:#f4f7f7}
h1{font-size:18px}.card{background:#fff;border:1px solid #e2e8e8;border-radius:12px;padding:14px;margin:12px 0}
input{width:100%;box-sizing:border-box;padding:10px;border:1px solid #cdd6d6;border-radius:8px;font-size:14px}
button{border:none;background:#0F766E;color:#fff;font-weight:700;padding:10px 14px;border-radius:9px;cursor:pointer;margin:4px 6px 0 0}
button.sec{background:#e7efef;color:#0F766E}pre{background:#0c1414;color:#d6f0ea;padding:12px;border-radius:8px;overflow:auto;font-size:12px}
.muted{color:#5b6b6b;font-size:12px}</style></head><body>
<h1>청주 시세 · 운영 관리자</h1>
<div class=card><label class=muted>관리자 토큰(ADMIN_TOKEN)</label>
<input id=tok type=password placeholder="서버 .env의 ADMIN_TOKEN"></div>
<div class=card>
<button onclick=call('/admin/monitor','GET')>🩺 시스템 상태(모니터링)</button>
<button class=sec onclick=call('/admin/runs','GET')>실행 이력</button>
<button onclick=call('/admin/status','GET')>좌표 커버리지 상태</button>
<button onclick=call('/admin/geocode','POST')>지오코딩 실행(전체)</button>
<button class=sec onclick=call('/admin/geocode?limit=50','POST')>지오코딩(50건)</button>
<button class=sec onclick=call('/admin/collect?geocode=true','POST')>수집+지오코딩</button>
<div class=muted style=margin-top:8px>실행은 백그라운드입니다. 진행/결과는 ‘상태’로 확인하세요.</div>
</div>
<pre id=out>결과가 여기에 표시됩니다.</pre>
<script>
async function call(path,method){const t=document.getElementById('tok').value.trim();
 const o=document.getElementById('out');o.textContent='요청 중…';
 try{const r=await fetch(path,{method,headers:{'X-Admin-Token':t}});
  const j=await r.json();o.textContent=JSON.stringify(j,null,2);}catch(e){o.textContent='오류: '+e;}}
</script></body></html>"""
