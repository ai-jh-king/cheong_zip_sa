"""배포/전달 전 단일 게이트 — 모든 정적 검증을 순서대로 실행하고 하나의 PASS/FAIL 을 준다.

샌드박스(무거운 런타임 의존성 없음)에서 '컴파일은 되는데 앱이 죽는' 사고를 막기 위한
최후의 방어선. 실패 항목이 하나라도 있으면 exit 1.

포함(모두 순수 정적 — 무거운 런타임 의존성 불필요, 어디서나 실행):
  1) compileall            — 문법(SyntaxError/IndentationError)
  2) verify_imports        — app.* import/속성 심볼 해석(존재하지 않는 심볼·def 유실 흡수)
  3) verify_frontend       — 프런트(main.jsx) 괄호 균형·구조

이 게이트는 런타임 로직(ReferenceError, DB 동작, 라이브 API)까지는 보장하지 못한다 →
브라우저 스모크 + pytest + verify_region_codes(라이브)는 TESTING.md 참조.

사용:  python -m scripts.verify_all
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("문법(compileall)", [sys.executable, "-m", "compileall", "-q", "app", "scripts"]),
    ("내부 import/속성 심볼", [sys.executable, "-m", "scripts.verify_imports"]),
    ("프런트 무결성", [sys.executable, "-m", "scripts.verify_frontend"]),
]
# 참고: verify_region_codes 는 실제 MOLIT API 를 호출하는 '라이브 검사'라 정적 게이트에서 제외.
#       (MOLIT 키가 있는 환경에서 `python -m scripts.verify_region_codes` 로 별도 확인)


def main() -> int:
    results = []
    for label, cmd in CHECKS:
        try:
            p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            ok = p.returncode == 0
        except Exception as e:  # 스크립트 부재 등
            ok, p = False, None
            tail = str(e)
        else:
            tail = (p.stdout or p.stderr or "").strip().splitlines()[-1:] or [""]
            tail = tail[0]
        results.append((label, ok, tail))
        print(f"  {'✅' if ok else '❌'} {label}: {tail}")

    failed = [r for r in results if not r[1]]
    print("")
    if failed:
        print(f"게이트 실패 ❌ — {len(failed)}개 항목. 위 오류를 고친 뒤 재실행하세요. (전달 금지)")
        return 1
    print("게이트 PASS ✅ — 정적 검증 통과. (런타임은 브라우저 스모크·pytest로 확인: TESTING.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
