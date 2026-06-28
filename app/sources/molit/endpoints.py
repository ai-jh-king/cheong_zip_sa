"""
국토교통부 실거래가 API 엔드포인트 레지스트리.

지침서 3.1: 매물 유형 전체를 다루므로 유형별 엔드포인트를 '모두' 연동한다.
⚠️ 지침서 9장 / 부록: API 경로·필드명은 추측 금지. 아래 경로는 공공데이터포털에
   공개된 통상값이나, 최초 구현 시 각 데이터셋 Swagger 로 '반드시' 재확인하고
   필요하면 path 만 수정한다 (필드 매핑은 normalize.py 에서 교정).

키:  (property_type, deal_type)
  property_type: apartment | officetel | rowhouse | detached
  deal_type:     trade(매매) | rent(전월세)  ← 전세/월세는 응답의 보증금·월세로 구분
"""

MOLIT_BASE = "https://apis.data.go.kr/1613000"

# operation 경로만 분리해 두어 Swagger 확인 후 한 곳만 고치면 되게 함.
MOLIT_ENDPOINTS: dict[tuple[str, str], dict] = {
    ("apartment", "trade"): {
        "path": "/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev",
        "source": "MOLIT_APT_TRADE",
    },
    ("apartment", "rent"): {
        "path": "/RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
        "source": "MOLIT_APT_RENT",
    },
    ("officetel", "trade"): {
        "path": "/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade",
        "source": "MOLIT_OFFI_TRADE",
    },
    ("officetel", "rent"): {
        "path": "/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent",
        "source": "MOLIT_OFFI_RENT",
    },
    ("rowhouse", "trade"): {
        "path": "/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade",
        "source": "MOLIT_RH_TRADE",
    },
    ("rowhouse", "rent"): {
        "path": "/RTMSDataSvcRHRent/getRTMSDataSvcRHRent",
        "source": "MOLIT_RH_RENT",
    },
    ("detached", "trade"): {
        "path": "/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade",
        "source": "MOLIT_SH_TRADE",
    },
    ("detached", "rent"): {
        "path": "/RTMSDataSvcSHRent/getRTMSDataSvcSHRent",
        "source": "MOLIT_SH_RENT",
    },
}

PROPERTY_TYPES = ["apartment", "officetel", "rowhouse", "detached"]
DEAL_FETCH_TYPES = ["trade", "rent"]
