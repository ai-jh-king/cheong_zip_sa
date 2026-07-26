"""단지 명칭 중복 의심 리포트(읽기 전용·왜곡 없음 가드).

배경(2026-07 조사): '같은 단지가 다른 표기로 중복 집계' 의심 사례를 전수 조사한 결과,
공백·괄호 변형은 0건, '아파트' 접미사만 다른 4쌍은 **전부 동(洞)이 다른 실제 별개 단지**
(효성=가경/복대동 vs 효성아파트=비하동 등), 차수 표기(2차·A단지)는 당연히 별개.
→ **이름 기반 자동 병합은 하지 않는다**(서로 다른 단지를 합쳐 시세를 왜곡할 위험이 실증됨).
이 스크립트는 수집 후 주기적으로 돌려 '진짜 중복'(이름 유사 + 동 일치 + 연식 일치)이
새로 생기는지 감시하는 용도. 발견 시에만 수동 검토로 처리한다.

사용: python -m scripts.dedup_names_report
"""
import re
import logging
from collections import defaultdict

from sqlalchemy import select, func

from app.db.session import init_db, SessionLocal
from app.models import Transaction

logging.basicConfig(level="INFO", format="%(message)s")
log = logging.getLogger("dedup_report")


def _norm(s: str) -> str:
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[()\[\]]", "", s)
    s = re.sub(r"(아파트|APT)$", "", s, flags=re.I)
    return s.lower()


def run() -> list:
    init_db()
    suspects = []
    with SessionLocal() as db:
        rows = db.execute(
            select(Transaction.complex_name, Transaction.lawd_cd,
                   Transaction.dong_name, Transaction.build_year, func.count())
            .where(Transaction.complex_name.isnot(None))
            .group_by(Transaction.complex_name, Transaction.lawd_cd,
                      Transaction.dong_name, Transaction.build_year)).all()
        # (정규화명, 구) 그룹에 서로 다른 원본명이 2개 이상이고 '동·연식까지 같은' 조합만 의심.
        groups = defaultdict(list)
        for name, lawd, dong, by, cnt in rows:
            groups[(_norm(name), lawd, dong, by)].append((name, cnt))
        for (nk, lawd, dong, by), items in groups.items():
            names = {n for n, _ in items}
            if len(names) > 1:
                suspects.append({"lawd_cd": lawd, "dong": dong, "build_year": by,
                                 "names": sorted(names),
                                 "counts": {n: c for n, c in items}})
    if not suspects:
        log.info("✅ 진짜 중복 의심(이름 변형+동 일치+연식 일치) 0건 — 병합 불필요.")
    else:
        log.info("⚠️ 수동 검토 필요 %d건:", len(suspects))
        for s in suspects:
            log.info("  %s %s %s년: %s", s["lawd_cd"], s["dong"], s["build_year"], s["names"])
    return suspects


if __name__ == "__main__":
    run()
