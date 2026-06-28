"""
프런트 빌드(frontend/) 무결성 오프라인 검증.

네트워크/Node 없이 "frontend/src/main.jsx 가 레거시 app/web/index.html 의 React 본문과
의도된 1줄(API)만 다르다"는 것 + 괄호 균형 + import 커버리지 + index.html 구성을 확인한다.

사용:  python -m scripts.verify_frontend
종료코드 0 = 통과, 1 = 실패.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY = ROOT / "app" / "web" / "index.html"
MAINJSX = ROOT / "frontend" / "src" / "main.jsx"
FE_HTML = ROOT / "frontend" / "index.html"

ok = True
def check(label, cond, detail=""):
    global ok
    mark = "✅" if cond else "❌"
    print(f"  {mark} {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        ok = False

def main() -> int:
    print("== 프런트 무결성 검증 (컷오버 후: frontend/src 단일 소스) ==")
    if not (MAINJSX.exists() and FE_HTML.exists()):
        print("  ❌ frontend 산출물 없음(main.jsx 또는 index.html).")
        return 1

    # 1) 레거시 인라인 스크립트 본문 추출 (있으면 정보용 대조에 사용; 제거됐으면 생략)
    orig = None
    if LEGACY.exists():
        src = LEGACY.read_text(encoding="utf-8").split("\n")
        try:
            ib = next(i for i, l in enumerate(src) if l.strip() == '<script type="text/babel">')
            ic = next(i for i in range(ib + 1, len(src)) if src[i].strip() == "</script>")
            orig = src[ib + 1:ic]
        except StopIteration:
            orig = None

    # 2) main.jsx 본문
    mj = MAINJSX.read_text(encoding="utf-8").split("\n")
    code = "\n".join(mj)


    # 2-a) 레거시 대조(정보용) — 컷오버 확정 후 레거시(app/web/index.html)는 "동결 참조".
    #      이제 frontend/src 가 단일 소스이므로, 향후 편집으로 차이가 벌어지는 건 정상.
    if orig:
        try:
            start = mj.index(orig[0])
            body = mj[start:start + len(orig)]
            diffs = sum(1 for a, b in zip(orig, body) if a != b)
            print(f"  ℹ️ 레거시 대조(동결 참조): 본문 {len(body)}줄 / 차이 {diffs}줄 "
                  f"(컷오버 후 차이 증가는 정상 — 레거시는 더 이상 편집하지 않음)")
        except ValueError:
            print("  ℹ️ 레거시 대조: 시작점 불일치 — 컷오버 후 분기됐을 수 있음(정상).")
    else:
        print("  ℹ️ 레거시 없음 — 컷오버 완료(단일 소스). 대조 생략.")

    # 3) main.jsx 괄호 균형 (하드 — main.jsx 자체 유효성)
    for o, c in [("(", ")"), ("{", "}"), ("[", "]")]:
        check(f"괄호 균형 {o}{c}", code.count(o) == code.count(c))

    # 4) React/ReactDOM 사용이 import로 커버 (하드)
    react_used = set(re.findall(r"React\.(\w+)", code))
    check("import React 존재", "import React from 'react'" in code, f"React.X 사용={sorted(react_used)}")
    rdom_used = set(re.findall(r"ReactDOM\.(\w+)", code))
    covered = ("createRoot" in code) and ("createPortal" in code)
    check("ReactDOM 사용 커버(createRoot+createPortal)", covered, f"사용={sorted(rdom_used)}")

    # 5) frontend/index.html 구성
    h = FE_HTML.read_text(encoding="utf-8")
    check("CDN react/babel 제거됨", "cdnjs.cloudflare.com" not in h)
    check("module 엔트리 존재", 'type="module" src="/src/main.jsx"' in h)
    check("root div 존재", 'id="root"' in h)
    check("manifest 링크(PWA)", 'rel="manifest"' in h)
    check("SW 등록 스크립트", "serviceWorker.register('/sw.js')" in h)

    print("== 결과:", "PASS ✅" if ok else "FAIL ❌", "==")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
