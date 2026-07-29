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

    # 6) 최상위 함수 중복 정의 탐지 — 같은 이름 재정의는 앞 정의를 덮어써 기존 사용처가 오동작(실제 사고: JeonseSafety)
    names = re.findall(r"^function\s+([A-Za-z_]\w*)\s*\(", code, re.M)
    dups = sorted({n for n in names if names.count(n) > 1})
    check("최상위 함수 중복 정의 없음", not dups, f"중복={dups}" if dups else "")

    # 7) React 훅 사용 정합 — 파일 안에서 `useX(` 호출된 훅이 import(또는 React 구조분해)로 들어와 있어야 한다.
    #    구조분해 안 된 훅을 그냥 호출하면 런타임 ReferenceError(실제 사고: v1.169 지도 탭 useRef 미포함=크래시).
    react_hooks = ("useState","useEffect","useMemo","useCallback","useRef",
                   "useReducer","useContext","useLayoutEffect","useTransition")
    imported = set()
    m = re.search(r"const\s*\{([^}]+)\}\s*=\s*React\s*;", code)
    if m:
        imported |= {t.strip() for t in m.group(1).split(",") if t.strip()}
    for h in re.findall(r"import\s*\{([^}]+)\}\s*from\s*['\"]react['\"]", code):
        imported |= {t.strip().split(" as ")[-1] for t in h.split(",") if t.strip()}
    used = {h for h in react_hooks if re.search(rf"(?<![A-Za-z_.]){h}\s*\(", code)}
    missing = sorted(used - imported)
    check("React 훅 import/구조분해 정합", not missing, f"누락(런타임 크래시)={missing}" if missing else "")

    # TDZ 방지: App 컴포넌트 안에서 useState 로 선언한 식별자를 '선언보다 앞줄'에서 쓰면
    # 런타임 ReferenceError("Cannot access 'x' before initialization")로 앱 전체가 크래시(실사고 v1.249).
    # 오프라인 검사(괄호·구문)로는 못 잡으므로 선언·사용 줄을 대조한다.
    # 범위: App 함수 본문만(다른 컴포넌트의 동명 변수 오탐 방지).
    tdz = []
    app_start = next((i for i, l in enumerate(mj) if re.match(r"^function App\s*\(", l)), None)
    if app_start is not None:
        app_end = next((i for i in range(app_start + 1, len(mj))
                        if re.match(r"^(function |const [A-Za-z_$][\w$]*\s*=\s*\()", mj[i])), len(mj))
        body = mj[app_start:app_end]
        decl_re = re.compile(r"^\s*const\s*\[\s*([A-Za-z_$][\w$]*)\s*,\s*set[\w$]*\s*\]\s*=\s*(?:React\.)?useState")
        decls = {}
        for i, line in enumerate(body):
            m = decl_re.match(line)
            if m and m.group(1) not in decls:
                decls[m.group(1)] = i
        for name, dline in decls.items():
            if len(name) < 3:                 # 1~2글자는 오탐 많아 제외
                continue
            pat = re.compile(rf"(?<![A-Za-z_$.]){re.escape(name)}(?![\w$])")
            for i in range(dline):
                line = body[i]
                if line.lstrip().startswith(("//", "*", "/*")):
                    continue
                if pat.search(line):
                    tdz.append(f"{name}: {app_start+i+1}행 사용 < {app_start+dline+1}행 선언")
                    break
    check("App useState 선언-사용 순서(TDZ)", not tdz, "; ".join(tdz[:3]) if tdz else "")

    print("== 결과:", "PASS ✅" if ok else "FAIL ❌", "==")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
