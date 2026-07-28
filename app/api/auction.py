"""경매·공매 안내 API.

- 법원 경매: 공식 Open API 부재 → 데이터 미제공(스크래핑 금지). 공식 링크·지식(도감)로 안내.
- 캠코 공매(온비드): data.go.kr 공식 API 연동(활용신청 필요). 미연동 시 connected=false + 안내.
"""
from fastapi import APIRouter

from app.sources.onbid import fetch_public_sale

router = APIRouter(prefix="/auction", tags=["auction"])

DISCLAIMER = ("공매(온비드) 물건 정보는 캠코 공식 API 기반 참고용이며, 입찰 조건·권리관계·명도 책임은 "
              "반드시 온비드 공고 원문과 등기부·현장 확인으로 검증해야 합니다. "
              "법원 경매는 공식 API가 없어 이 앱이 물건 데이터를 제공하지 않습니다(대법원 법원경매정보에서 확인). "
              "청집사는 입찰을 권유하지 않으며 어떤 수수료도 받지 않습니다.")

LINKS = [
    {"name": "대법원 법원경매정보", "desc": "법원 경매 물건·기일·매각통계 공식 조회", "url": "https://www.courtauction.go.kr"},
    {"name": "온비드(캠코 공매)", "desc": "압류재산 등 공매 입찰 — 한국자산관리공사", "url": "https://www.onbid.co.kr"},
    {"name": "등기부등본 열람", "desc": "권리분석의 시작 — 인터넷등기소", "url": "https://www.iros.go.kr"},
]


@router.get("/public-sale")
def public_sale():
    """청주 소재 온비드 공매 물건(연동 시). 미연동이어도 링크·안내는 항상 제공."""
    items = fetch_public_sale("청주")
    return {"connected": items is not None, "items": items or [],
            "notice": None if items is not None else
            "온비드 공매 API가 아직 연동되지 않았어요(공공데이터포털 활용신청 필요). 공식 사이트에서 직접 확인할 수 있어요.",
            "links": LINKS, "disclaimer": DISCLAIMER}
