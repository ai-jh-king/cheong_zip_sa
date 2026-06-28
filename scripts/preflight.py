"""배포 전 점검(preflight) — '인터넷에 노출해도 안전한가' 중심.

doctor.py(데이터·시스템 헬스)와 역할이 다르다:
- doctor : DB 연결·지역코드·키 연동·수집 커버리지·백업 등 '작동하는가'.
- preflight: 시크릿 강도·CORS·env·빌드·법적 페이지 등 '공개 출시 안전한가'.

특징: 앱 패키지(fastapi 등) import 없이 동작 — os.environ + (있으면).env + 파일 존재만 본다.
       운영 배포 환경에서 실행해야 의미가 있다(거기 실제 env가 있으므로).

사용:  python -m scripts.preflight
종료코드: FAIL 1개라도 있으면 1(파이프라인에서 게이트로 사용 가능).
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
_MARK = {PASS: "✅", WARN: "⚠️ ", FAIL: "❌"}
_results: list[tuple[str, str, str]] = []


def add(status: str, label: str, detail: str = "") -> None:
    _results.append((status, label, detail))
    print(f"  {_MARK[status]} [{status}] {label}" + (f" — {detail}" if detail else ""))


def _load_dotenv(path: Path) -> dict:
    """간단 .env 파서(따옴표·주석 처리). pydantic-settings가 .env를 읽는 것과 동일 취지."""
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        env[k.strip()] = v
    return env


_DOTENV = _load_dotenv(ROOT / ".env")


def env(name: str, default: str = "") -> str:
    """os.environ 우선, 없으면 .env 파일."""
    return os.environ.get(name, _DOTENV.get(name, default)).strip()


def _is_prod(app_env: str) -> bool:
    return app_env.lower() in ("prod", "production", "live")


def main() -> int:
    app_env = env("APP_ENV", "local")
    prod = _is_prod(app_env)
    print(f"\n=== 배포 전 점검 (preflight) · APP_ENV={app_env or '(미설정)'} ===\n")

    # 1) 운영 환경 표기
    if prod:
        add(PASS, "APP_ENV", f"{app_env}")
    else:
        add(WARN, "APP_ENV", f"'{app_env or 'local'}' — 운영 출시면 prod 로 설정 권장")

    # 2) JWT_SECRET(세션 서명) — 설정 + 충분한 길이 필수
    jwt = env("JWT_SECRET")
    if not jwt:
        add(FAIL, "JWT_SECRET", "미설정 — 세션 토큰이 안전하지 않음. 길고 무작위로 설정")
    elif len(jwt) < 32:
        add(FAIL, "JWT_SECRET", f"너무 짧음({len(jwt)}자) — 32자 이상 무작위 권장")
    elif jwt.lower() in ("changeme", "secret", "devsecret", "test"):
        add(FAIL, "JWT_SECRET", "기본/추측가능 값 — 무작위로 교체")
    else:
        add(PASS, "JWT_SECRET", f"설정됨({len(jwt)}자)")

    # 3) ADMIN_TOKEN — 미설정이면 관리자 API 비활성(안전). 설정 시 충분히 길어야.
    adm = env("ADMIN_TOKEN")
    if not adm:
        add(WARN, "ADMIN_TOKEN", "미설정 — /admin/* 비활성(안전). 운영 관리가 필요하면 길게 설정")
    elif len(adm) < 16:
        add(FAIL, "ADMIN_TOKEN", f"너무 짧음({len(adm)}자) — 16자 이상 권장(관리자 API 노출 위험)")
    else:
        add(PASS, "ADMIN_TOKEN", f"설정됨({len(adm)}자)")

    # 4) CORS_ORIGINS — 비어있으면 main.py가 '*'(전체 허용). 운영은 좁혀야.
    cors = env("CORS_ORIGINS")
    if not cors or cors == "*":
        add(FAIL if prod else WARN, "CORS_ORIGINS",
            "와일드카드(*) — 운영 도메인으로 좁히세요. 예: https://도메인,capacitor://localhost")
    else:
        origins = [o for o in cors.split(",") if o.strip()]
        insecure = [o for o in origins if o.startswith("http://") and "localhost" not in o and "127.0.0.1" not in o]
        if insecure:
            add(WARN, "CORS_ORIGINS", f"http(비암호화) 오리진 포함: {', '.join(insecure)}")
        else:
            add(PASS, "CORS_ORIGINS", f"{len(origins)}개 지정")

    # 5) DATABASE_URL — 미설정이면 SQLite 폴백. 운영 다중워커는 PostgreSQL 권장.
    dburl = env("DATABASE_URL")
    if not dburl:
        add(WARN, "DATABASE_URL", "미설정 → SQLite 폴백. 운영(다중워커/동시쓰기)은 PostgreSQL 권장")
    elif dburl.startswith("sqlite"):
        add(WARN, "DATABASE_URL", "SQLite — 단일 인스턴스만. 확장 시 PostgreSQL 권장")
    else:
        add(PASS, "DATABASE_URL", "외부 DB 지정됨")

    # 6) MOLIT_SERVICE_KEY — 없으면 실거래 데이터 없음(데모만).
    if env("MOLIT_SERVICE_KEY"):
        add(PASS, "MOLIT_SERVICE_KEY", "설정됨(실데이터 수집 가능)")
    else:
        add(FAIL if prod else WARN, "MOLIT_SERVICE_KEY",
            "미설정 — 실거래 데이터 없음(데모만 표시). data.go.kr 활용신청 후 설정")

    # 7) 프런트 빌드(SPA) — WEB_DIR=dist 로 서빙할 경우 dist/assets 필요.
    web_dir = env("WEB_DIR")
    if web_dir:
        assets = Path(web_dir) / "assets"
        idx = Path(web_dir) / "index.html"
        if assets.is_dir() and idx.exists():
            add(PASS, "WEB_DIR(SPA)", f"{web_dir} (빌드 산출물 확인)")
        else:
            add(FAIL, "WEB_DIR(SPA)", f"{web_dir} 에 assets/index.html 없음 — frontend 빌드(npm run build) 필요")
    else:
        add(WARN, "WEB_DIR(SPA)", "미설정 — 레거시 app/web 서빙 또는 리버스프록시로 dist 서빙 중인지 확인")

    # 8) 법적 페이지 존재
    legal_ok = (ROOT / "app/web/legal/privacy.md").exists() and (ROOT / "app/web/legal/terms.md").exists()
    add(PASS if legal_ok else FAIL, "법적 페이지",
        "개인정보처리방침·이용약관 존재(내용은 법무 검토 권장)" if legal_ok else "privacy.md/terms.md 누락")

    # 9) 아이콘 존재 + 플레이스홀더 경고
    icons = list((ROOT / "frontend/public/icons").glob("*.png")) if (ROOT / "frontend/public/icons").is_dir() else []
    if not icons:
        add(WARN, "앱 아이콘", "frontend/public/icons 비어있음 — 스토어/PWA 아이콘 필요")
    else:
        small = [p.name for p in icons if p.stat().st_size < 8000]
        if small:
            add(WARN, "앱 아이콘", f"플레이스홀더 가능성(작은 파일): {', '.join(small)} — 실제 브랜드 아이콘으로 교체")
        else:
            add(PASS, "앱 아이콘", f"{len(icons)}개")

    # 요약 + 다음 단계 안내
    n_fail = sum(1 for s, _, _ in _results if s == FAIL)
    n_warn = sum(1 for s, _, _ in _results if s == WARN)
    print(f"\n=== 결과: FAIL {n_fail} · WARN {n_warn} · 총 {len(_results)} 점검 ===")
    print("\n[운영자가 추가로 직접 해야 하는 것 — 이 스크립트로 검증 불가]")
    for line in (
        "· 서버에 HTTPS/도메인 적용(TLS).",
        "· DB 마이그레이션: `python -m scripts.db_upgrade` 또는 `alembic upgrade head`.",
        "· 데이터·시스템 헬스: `python -m scripts.doctor` 로 별도 점검.",
        "· 수집 실행: `python -m scripts.run_collect live` 후 `/status/data` 커버리지 확인.",
        "· 프런트 검증: `python -m scripts.verify_frontend`.",
        "· 개인정보처리방침·약관 내용 법무 검토(특히 대출 민감정보 9.A).",
    ):
        print("  " + line)
    if n_fail:
        print(f"\n❌ FAIL {n_fail}건 — 해결 후 출시하세요.")
        return 1
    print("\n✅ 차단(FAIL) 항목 없음. WARN 항목 검토 후 출시 진행 가능.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
