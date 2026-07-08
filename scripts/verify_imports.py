"""내부 import 심볼 정적 검증 — 런타임 ImportError/부팅 실패를 사전 차단.

배경: `from app.services.stats import complex_detail` 처럼 **존재하지 않는 심볼**을
import하면 compileall/py_compile 은 통과하지만(문법은 정상) 실제 앱 로드 시
ImportError 로 죽는다. 실제 사고: AGG_MONTHS(v1.162)·complex_detail(누락 복구).
sqlalchemy 등 무거운 의존성 없이 순수 AST 로 `app.*` 내부 import 를 해석한다.

사용:  python -m scripts.verify_imports      # 문제 있으면 exit 1
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


def _module_path(mod: str) -> Path | None:
    rel = mod.replace(".", "/")
    for cand in (ROOT / f"{rel}.py", ROOT / rel / "__init__.py"):
        if cand.exists():
            return cand
    return None


def _toplevel_names(path: Path) -> set[str]:
    """모듈 최상위에 정의/재노출된 이름 집합(def·class·할당·import·__all__ 대응)."""
    names: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            names.add(n.target.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                names.add(a.asname or a.name.split(".")[0])
    return names


def main() -> int:
    problems: list[str] = []
    cache: dict[str, set[str]] = {}

    def names_of(mod: str) -> set[str] | None:
        tgt = _module_path(mod)
        if tgt is None:
            return None
        if mod not in cache:
            cache[mod] = _toplevel_names(tgt)
        return cache[mod]

    for py in APP.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"))
        rel = py.relative_to(ROOT)

        # 이 파일에서 'app.*' 모듈에 붙은 로컬 별칭 맵 (from app.services import stats / import app.x as y)
        alias: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.") and not node.level:
                for a in node.names:
                    if _module_path(f"{node.module}.{a.name}") is not None:
                        alias[a.asname or a.name] = f"{node.module}.{a.name}"
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.startswith("app.") and _module_path(a.name) is not None:
                        alias[a.asname or a.name.split(".")[0]] = a.name

        for node in ast.walk(tree):
            # (1) from app.X import a,b  — a,b 가 실제 정의됐는지
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.") and not node.level:
                defined = names_of(node.module)
                if defined is None:
                    continue
                for a in node.names:
                    if a.name == "*" or a.name in defined:
                        continue
                    if _module_path(f"{node.module}.{a.name}") is not None:
                        continue  # 서브모듈 import
                    problems.append(f"{rel}:{node.lineno}  ❌ import '{a.name}' 없음 in {node.module}")
            # (2) module.attr 접근 — attr 가 그 모듈에 실제 있는지 (예: stats.complex_detail)
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in alias:
                mod = alias[node.value.id]
                defined = names_of(mod)
                if defined is None:
                    continue
                if node.attr not in defined and _module_path(f"{mod}.{node.attr}") is None:
                    problems.append(f"{rel}:{node.lineno}  ❌ '{node.value.id}.{node.attr}' — {mod} 에 '{node.attr}' 없음")

    if problems:
        # 중복 제거(같은 심볼 반복 접근)
        seen, uniq = set(), []
        for p in problems:
            if p not in seen:
                seen.add(p); uniq.append(p)
        print("내부 import/속성 검증 실패 — 존재하지 않는 심볼:")
        for p in uniq:
            print("  " + p)
        print(f"\n총 {len(uniq)}건. (compileall 은 통과하지만 런타임에 앱이 죽습니다)")
        return 1
    print("내부 import/속성 검증 PASS ✅ — app.* 심볼 모두 해석됨")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
