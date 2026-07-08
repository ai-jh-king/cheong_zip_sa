"""실제 앱 end-to-end 스모크 — TestClient 로 실제 HTTP 요청을 던져 사용자 여정을 검증.
샘플 데이터를 넣고 시세→단지상세→호가검증→급매→게시판(주민)→온보딩을 통과시킨다.

실행:  JWT_SECRET=... AUTH_DEV_LOGIN=true python -m scripts.smoke_e2e
(DATABASE_URL 미설정 시 임시 SQLite 파일 사용)
"""
import os
import tempfile
from datetime import date, timedelta

os.environ.setdefault("JWT_SECRET", "smoke_secret_key_at_least_32_chars_long_ok")
os.environ.setdefault("AUTH_DEV_LOGIN", "true")
if not os.environ.get("DATABASE_URL"):
    _f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    os.environ["DATABASE_URL"] = f"sqlite:///{_f.name}"

from fastapi.testclient import TestClient           # noqa: E402
from app.main import app                            # noqa: E402
from app.db.session import SessionLocal, init_db    # noqa: E402
from app.models import Region, Complex, Transaction, UserPref, DeviceLink  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'✅' if cond else '❌'} {name}" + (f" — {detail}" if detail and not cond else ""))


def seed():
    init_db()
    db = SessionLocal()
    try:
        if not db.get(Region, "43113"):
            db.add(Region(lawd_cd="43113", sido="충청북도", sigungu="청주시 흥덕구", dong="복대동"))
        db.add(Complex(name="테스트자이", lawd_cd="43113", property_type="apartment",
                       build_year=2015, households=800, lat=36.64, lng=127.42))
        base = date.today().replace(day=1)
        # 12개월치 매매 + 전세(전세가율·추이·호가검증·급매 재료)
        for m in range(12):
            mon = (base - timedelta(days=30 * m))
            amt = 50000 + m * 300
            db.add(Transaction(lawd_cd="43113", property_type="apartment", deal_type="trade",
                               complex_name="테스트자이", exclusive_area=84.9, floor=10 - (m % 5),
                               contract_date=mon, deal_amount=amt, source="SMOKE",
                               dedup_key=f"t{m}"))
            db.add(Transaction(lawd_cd="43113", property_type="apartment", deal_type="jeonse",
                               complex_name="테스트자이", exclusive_area=84.9, floor=7,
                               contract_date=mon, deposit=int(amt * 0.85), source="SMOKE",
                               dedup_key=f"j{m}"))
        # 급매 후보: 같은 평형 최근 저가 1건
        db.add(Transaction(lawd_cd="43113", property_type="apartment", deal_type="trade",
                           complex_name="테스트자이", exclusive_area=84.9, floor=1,
                           contract_date=base, deal_amount=42000, source="SMOKE", dedup_key="bargain"))
        db.commit()
    finally:
        db.close()


def main():
    seed()
    c = TestClient(app)

    print("\n[1] 헬스·기본")
    r = c.get("/health"); check("GET /health 200", r.status_code == 200)

    print("\n[2] 시세 대시보드")
    r = c.get("/dashboard/summary")
    check("GET /dashboard/summary 200", r.status_code == 200, r.text[:120])

    print("\n[3] 단지 상세(전세가율 신호·추이)")
    r = c.get("/complex/detail", params={"name": "테스트자이", "lawd_cd": "43113",
                                         "property_type": "apartment"})
    j = r.json() if r.status_code == 200 else {}
    check("GET /complex/detail 200", r.status_code == 200, r.text[:120])
    check("  found=True", j.get("found") is True)
    check("  rent_signal 존재·해석", bool(j.get("rent_signal")) and j["rent_signal"].get("level") in ("high", "elevated", "normal", "low"))
    check("  timeseries≥2(추이)", len(j.get("timeseries") or []) >= 2)

    print("\n[4] 호가 검증(가격이 분포 어디쯤)")
    r = c.get("/pricecheck/quote", params={"name": "테스트자이", "lawd_cd": "43113", "asking": 56000})
    j = r.json() if r.status_code == 200 else {}
    check("GET /pricecheck/quote 200", r.status_code == 200, r.text[:120])
    check("  found + percentile 계산", j.get("found") is True and isinstance(j.get("percentile"), int))
    check("  면책 포함(왜곡 없음)", "단정" in (j.get("disclaimer") or ""))

    print("\n[5] 급매 레이더")
    r = c.get("/pricecheck/bargains")
    j = r.json() if r.status_code == 200 else {}
    check("GET /pricecheck/bargains 200", r.status_code == 200)
    check("  낮은가격 거래 포착 + 고지", isinstance(j.get("items"), list) and "단정하지" in (j.get("disclaimer") or ""))
    check("  급매 항목에 좌표(지도 핀 재료)", all("lat" in x for x in (j.get("items") or [])) )

    print("\n[6] 게시판 — 로그인→우리집→주민 뱃지(서버 대조)")
    lr = c.post("/auth/dev-login", json={"device_id": "smoke-dev", "nickname": "스모크"})
    tok = (lr.json() or {}).get("token")
    check("POST /auth/dev-login 200+token", lr.status_code == 200 and bool(tok))
    # 우리집 설정(prefs) — dev 기기에 my_home
    db = SessionLocal()
    try:
        db.add(UserPref(device_id="smoke-dev",
                        data={"my_home": {"complex_name": "테스트자이", "lawd_cd": "43113"}}))
        db.commit()
    finally:
        db.close()
    h = {"Authorization": f"Bearer {tok}"}
    pr = c.post("/community/posts", headers=h,
                json={"title": "우리 단지 이야기", "body": "주차 어떤가요", "category": "free",
                      "complex_name": "테스트자이", "lawd_cd": "43113"})
    pj = pr.json() if pr.status_code == 200 else {}
    check("POST /community/posts 200", pr.status_code == 200, pr.text[:160])
    check("  resident=True(우리집=단지 서버검증)", (pj.get("post") or {}).get("resident") is True)
    r = c.get("/community/posts", params={"complex": "테스트자이"})
    check("  GET /community/posts?complex= 필터", r.status_code == 200 and len(r.json().get("items", [])) >= 1)

    print("\n[7] 게시판 no such column 재발 없음(resident 컬럼 존재)")
    r = c.get("/community/posts")
    check("GET /community/posts 200(컬럼 정상)", r.status_code == 200, r.text[:160])

    print("\n[8] 온보딩(전입자)")
    r = c.get("/onboarding/options")
    check("GET /onboarding/options 200", r.status_code == 200)

    print("\n" + "=" * 52)
    print(f"결과: {len(PASS)} PASS · {len(FAIL)} FAIL")
    if FAIL:
        print("실패:", ", ".join(FAIL))
        return 1
    print("✅ 실제 앱 e2e 스모크 전부 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
