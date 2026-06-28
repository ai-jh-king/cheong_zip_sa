"""
개발/오프라인 검증용 모의 실거래 데이터.

⚠️ 매우 중요: 아래 값은 '실제 시세가 아니다'. 파이프라인(정규화·적재·집계·화면)이
   동작하는지 확인하기 위한 가짜 표본이며, DB 적재 시 is_sample=True / source='FIXTURE'
   로 표식되어 실데이터와 절대 섞이지 않는다. 키 발급 후 collect_live 로 교체된다.

각 row 는 국토부 XML 을 파싱한 '원본 dict' 형태를 흉내 낸다(필드명 그대로).
실제 Swagger 확인 시 필드명이 다르면 normalize.FIELD_CANDIDATES 만 보강하면 된다.
"""

RAW_FIXTURES = [
    # --- 아파트 매매 (상당구) ---
    {"property_type": "apartment", "deal_fetch_type": "trade", "lawd_cd": "43111",
     "source": "MOLIT_APT_TRADE",
     "row": {"aptNm": "샘플그린아파트", "umdNm": "용암동", "excluUseAr": "84.97",
             "floor": "12", "buildYear": "2009", "dealYear": "2025",
             "dealMonth": "11", "dealDay": "5", "dealAmount": "31,500"}},
    {"property_type": "apartment", "deal_fetch_type": "trade", "lawd_cd": "43111",
     "source": "MOLIT_APT_TRADE",
     "row": {"aptNm": "샘플그린아파트", "umdNm": "용암동", "excluUseAr": "84.97",
             "floor": "7", "buildYear": "2009", "dealYear": "2025",
             "dealMonth": "10", "dealDay": "18", "dealAmount": "30,800"}},
    # --- 아파트 전월세 (흥덕구): 전세 + 월세 ---
    {"property_type": "apartment", "deal_fetch_type": "rent", "lawd_cd": "43113",
     "source": "MOLIT_APT_RENT",
     "row": {"aptNm": "샘플리버뷰", "umdNm": "복대동", "excluUseAr": "59.92",
             "floor": "9", "buildYear": "2015", "dealYear": "2025",
             "dealMonth": "11", "dealDay": "3", "deposit": "23,000", "monthlyRent": "0"}},
    {"property_type": "apartment", "deal_fetch_type": "rent", "lawd_cd": "43113",
     "source": "MOLIT_APT_RENT",
     "row": {"aptNm": "샘플리버뷰", "umdNm": "복대동", "excluUseAr": "59.92",
             "floor": "4", "buildYear": "2015", "dealYear": "2025",
             "dealMonth": "11", "dealDay": "9", "deposit": "5,000", "monthlyRent": "65"}},
    # --- 오피스텔 매매 (서원구) ---
    {"property_type": "officetel", "deal_fetch_type": "trade", "lawd_cd": "43112",
     "source": "MOLIT_OFFI_TRADE",
     "row": {"offiNm": "샘플센트럴오피스텔", "umdNm": "산남동", "excluUseAr": "23.14",
             "floor": "8", "buildYear": "2018", "dealYear": "2025",
             "dealMonth": "10", "dealDay": "22", "dealAmount": "9,800"}},
    # --- 연립·다세대 매매 (청원구) ---
    {"property_type": "rowhouse", "deal_fetch_type": "trade", "lawd_cd": "43114",
     "source": "MOLIT_RH_TRADE",
     "row": {"mhouseNm": "샘플빌라", "umdNm": "오창읍", "excluUseAr": "49.50",
             "floor": "3", "buildYear": "2012", "dealYear": "2025",
             "dealMonth": "11", "dealDay": "1", "dealAmount": "14,200"}},
    # --- 단독·다가구 매매 (상당구): 단지명/지번 일부만 제공되는 케이스 ---
    {"property_type": "detached", "deal_fetch_type": "trade", "lawd_cd": "43111",
     "source": "MOLIT_SH_TRADE",
     "row": {"umdNm": "남일면", "연면적": "112.30", "buildYear": "2001",
             "dealYear": "2025", "dealMonth": "9", "dealDay": "14", "dealAmount": "26,000"}},
]


# --- 대시보드(집계) 검증용 월별 아파트 매매 시계열 (모의) ---------------------
# 각 구의 대략적 수준 + 월별 미세 변동. 실시세 아님 / is_sample=True 로 적재됨.
# 이게 있어야 전월대비·추이가 '실제 계산'으로 채워지는 걸 확인할 수 있다.
def _gen_monthly_series() -> list[dict]:
    base = {  # (구코드, 단지명, 동, 기준 만원, 월변동)
        "43111": ("샘플그린아파트", "용암동", 31200, 240),
        "43112": ("샘플파크자이", "분평동", 29900, -20),
        "43113": ("샘플리버뷰", "복대동", 33800, 360),
        "43114": ("샘플숲속마을", "내수읍", 27800, -60),
    }
    months = [(2025, 8), (2025, 9), (2025, 10), (2025, 11)]
    rows = []
    for code, (cx, dong, start, step) in base.items():
        for i, (yy, mm) in enumerate(months):
            amt = start + step * i
            rows.append({
                "property_type": "apartment", "deal_fetch_type": "trade",
                "lawd_cd": code, "source": "MOLIT_APT_TRADE",
                "row": {"aptNm": cx, "umdNm": dong, "excluUseAr": "84.90",
                        "floor": str(7 + i), "buildYear": "2012",
                        "dealYear": str(yy), "dealMonth": str(mm), "dealDay": "15",
                        "dealAmount": f"{amt:,}"},
            })
    return rows


RAW_FIXTURES += _gen_monthly_series()
