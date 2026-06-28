"""
지역코드 검증 (지침서 3.4 — 첫 구현 시 '반드시' 수행).
각 구 코드로 최근월 아파트 매매를 1회 조회해, 응답이 비지 않는지 확인한다.
응답이 계속 비면 코드가 틀렸을 가능성 → code.go.kr 에서 재확인.

사용법: python -m scripts.verify_region_codes   (MOLIT_SERVICE_KEY 필요)
"""
import logging
from datetime import date

from app.core.config import get_settings
from app.data.region_codes import CHEONGJU_DISTRICTS
from app.sources.molit.client import MolitClient, MolitKeyMissingError, MolitAuthError

logging.basicConfig(level="INFO")


def main() -> int:
    s = get_settings()
    if not s.molit_enabled:
        print("MOLIT_SERVICE_KEY 가 없어 검증할 수 없습니다. .env 설정 후 다시 실행하세요.")
        return 1

    client = MolitClient()
    ymd = (date.today().replace(day=1)).strftime("%Y%m")
    # 최근월은 신고 전일 수 있으니 한 달 전으로 점검
    y, m = (int(ymd[:4]), int(ymd[4:]) - 1)
    if m == 0:
        y, m = y - 1, 12
    check_ymd = f"{y}{m:02d}"

    print(f"검증 대상 계약년월: {check_ymd}\n")
    all_ok = True
    for d in CHEONGJU_DISTRICTS:
        try:
            items, _ = client.fetch("apartment", "trade", d.code, check_ymd)
            status = "OK" if items else "빈 응답(코드 의심 또는 거래 없음)"
            if not items:
                all_ok = False
            print(f"  [{d.code}] 청주시 {d.name}: {len(items)}건 → {status}")
        except MolitAuthError as e:
            print("\n인증 거부:", e)
            return 1
        except MolitKeyMissingError as e:
            print("실패:", e)
            return 1

    print("\n결론:",
          "모든 구 정상." if all_ok else
          "빈 응답 구 존재 → 다른 달로 재시도하거나 code.go.kr 에서 코드 재확인.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
