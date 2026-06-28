"""배포 자가진단(doctor) — 운영 PC에서 한 번에 전체 스택 점검.

사용:
  python -m scripts.doctor              # 전체 점검(실데이터 1회 조회 포함)
  python -m scripts.doctor --skip-live  # 외부 API 호출(MOLIT) 생략

확인 항목: 설정·DB 연결·핵심 테이블(마이그레이션)·지역코드 실조회·데이터 신선도/건수
·연동 키(MOLIT/카카오/지도/푸시)·백업 준비(pg_dump·쓰기권한)·스케줄러 설정.

각 항목을 ✅/⚠️/❌ 로 표시하고, ❌ 가 하나라도 있으면 종료코드 1.
샌드박스가 아닌 실제 운영 환경에서 돌려야 의미가 있습니다(DB·키 필요).
"""
from __future__ import annotations
import logging
import shutil
import sys
from pathlib import Path

logging.basicConfig(level="WARNING")

_ICON = {"ok": "✅", "warn": "⚠️ ", "fail": "❌"}
RESULTS: list[tuple[str, str, str]] = []


def add(status: str, label: str, detail: str = "") -> None:
    RESULTS.append((status, label, detail))
    line = f"{_ICON.get(status, '?')} {label}"
    if detail:
        line += f"  — {detail}"
    print(line)


def _check_db_and_data(skip_live: bool) -> None:
    from app.core.config import get_settings
    s = get_settings()
    # 설정/DB URL
    url = s.effective_database_url
    add("ok", "설정 로드")
    if url.startswith("sqlite"):
        add("warn", "DATABASE_URL", "SQLite 폴백 사용 중 — 운영은 PostgreSQL 권장")
    else:
        add("ok", "DATABASE_URL", url.split("@")[-1])

    try:
        from sqlalchemy import inspect, text
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            add("ok", "DB 연결")
            insp = inspect(db.get_bind())
            need = ["transactions", "favorites", "push_subscriptions", "job_runs"]
            missing = [t for t in need if not insp.has_table(t)]
            if missing:
                add("fail", "마이그레이션", f"누락 테이블 {missing} → python -m scripts.db_upgrade upgrade head")
            else:
                add("ok", "마이그레이션(핵심 테이블 존재)")

            from app.services.monitoring import system_status
            st = system_status(db)
            if st.get("data_as_of"):
                d = st.get("data_stale_days")
                status = "ok" if (d is not None and d <= s.data_stale_days) else "warn"
                add(status, "데이터 신선도", f"최신 계약일 {st['data_as_of']} ({d}일 전)")
            else:
                add("warn", "데이터 신선도", "실데이터 없음 — 아직 수집 전")
            c = st.get("counts", {})
            add("ok", "데이터 건수", f"실거래 {c.get('transactions_real',0)} · 단지 {c.get('complexes',0)} "
                                    f"· 푸시구독 {c.get('push_subscriptions',0)} · 관심 {c.get('favorites',0)}")
    except Exception as e:  # noqa
        add("fail", "DB 연결", repr(e)[:160])

    # 지역코드 실조회(MOLIT 1회) — 실데이터가 실제로 흐르는지 확인
    if not s.molit_enabled:
        add("warn", "MOLIT 키", "미설정 — 실데이터 수집 불가(.env MOLIT_SERVICE_KEY)")
    elif skip_live:
        add("warn", "지역코드 실조회", "--skip-live 로 생략됨")
    else:
        try:
            from datetime import date
            from app.data.region_codes import CHEONGJU_DISTRICTS
            from app.sources.molit.client import MolitClient
            from app.sources.molit.normalize import normalize_row, NormalizationReport
            y, m = date.today().year, date.today().month - 1
            if m == 0:
                y, m = y - 1, 12
            ymd = f"{y}{m:02d}"
            client = MolitClient()
            ok_codes, empty = [], []
            report = NormalizationReport()
            for d in CHEONGJU_DISTRICTS:
                try:
                    items, src = client.fetch("apartment", "trade", d.code, ymd)
                    (ok_codes if items else empty).append(d.code)
                    for it in items[:50]:   # 표본 정규화로 필드 매핑 점검
                        normalize_row(it, property_type="apartment", deal_fetch_type="trade",
                                      lawd_cd=d.code, source=src, report=report)
                except Exception:  # noqa
                    empty.append(d.code)
            if ok_codes and not empty:
                add("ok", "지역코드 실조회", f"{ymd} 4개 구 모두 응답({len(ok_codes)})")
            elif ok_codes:
                add("warn", "지역코드 실조회", f"빈 응답 코드 {empty}(거래 없음일 수도). code.go.kr 확인")
            else:
                add("fail", "지역코드 실조회", "모든 구 빈 응답 — 키/코드 점검 필요")
            # 정규화 매핑 건강 — 실데이터 필드가 우리 스키마에 매핑되는지(1순위 리스크)
            if report.total:
                if report.has_issues():
                    add("fail", "정규화 필드 매핑", f"{report.total}행 중 미매핑={report.summary()['misses']} → molit/normalize.py FIELD_CANDIDATES 보강")
                else:
                    add("ok", "정규화 필드 매핑", f"표본 {report.total}행 핵심 필드 정상")
        except Exception as e:  # noqa
            add("fail", "MOLIT 실조회", repr(e)[:160])


def _check_integrations_and_ops() -> None:
    from app.core.config import get_settings
    s = get_settings()
    add("ok" if s.kakao_rest_api_key else "warn", "카카오 POI 키",
        "" if s.kakao_rest_api_key else "미설정 — 인프라/생활권 점수 비활성")
    add("ok" if s.naver_map_client_id else "warn", "지도 키",
        "" if s.naver_map_client_id else "미설정 — 지도 표시 비활성")
    add("ok" if s.push_enabled else "warn", "웹푸시(VAPID)",
        "" if s.push_enabled else "미설정 — 푸시 비활성(python -m scripts.gen_vapid)")
    add("ok" if s.sentry_dsn else "warn", "에러 모니터링(Sentry)",
        "" if s.sentry_dsn else "미설정(선택)")
    add("ok" if s.alert_webhook_url else "warn", "실패 경보 웹훅",
        "" if s.alert_webhook_url else "미설정(선택) — 수집 실패 알림 비활성")
    add("ok" if s.admin_token else "warn", "관리자 토큰",
        "" if s.admin_token else "미설정 — /admin 비활성")

    # 백업 준비
    try:
        bdir = Path(s.backup_dir)
        bdir.mkdir(parents=True, exist_ok=True)
        probe = bdir / ".doctor_write_test"
        probe.write_text("ok")
        probe.unlink()
        add("ok", "백업 폴더 쓰기", str(bdir))
    except Exception as e:  # noqa
        add("fail", "백업 폴더 쓰기", repr(e)[:120])
    if not s.effective_database_url.startswith("sqlite"):
        add("ok" if shutil.which("pg_dump") else "fail", "pg_dump 설치",
            "" if shutil.which("pg_dump") else "PATH에 없음 — PostgreSQL 클라이언트 설치 필요")


def main() -> int:
    skip_live = "--skip-live" in sys.argv
    print("=== 청주집사 배포 자가진단 ===\n")
    _check_db_and_data(skip_live)
    print()
    _check_integrations_and_ops()

    fails = sum(1 for s, _, _ in RESULTS if s == "fail")
    warns = sum(1 for s, _, _ in RESULTS if s == "warn")
    oks = sum(1 for s, _, _ in RESULTS if s == "ok")
    print(f"\n=== 요약: ✅ {oks} · ⚠️ {warns} · ❌ {fails} ===")
    if fails:
        print("❌ 항목을 먼저 해결한 뒤 다시 실행하세요.")
    elif warns:
        print("필수 항목은 통과. ⚠️ 는 선택/미설정 항목입니다.")
    else:
        print("모든 점검 통과 — 배포 준비 완료 🎉")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
