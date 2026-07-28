"""금융·임차인 보호 규정 룰 (청주 적용 기준) — 하드코딩 금지 원칙에 따라 데이터로 분리.

⚠️ 왜곡 없음 원칙:
- 모든 수치는 법령·공식 공고의 공개 값이며 as_of(기준일)를 함께 표기한다.
- 정책 상품 요건·한도는 공고마다 바뀐다 → UI는 항상 '변동 가능·공식 확인 필수'를 표시하고
  official_url 로 연결한다. 이 파일은 '해당 가능성 안내'용이지 심사·보장 판정이 아니다.
- 개정 반영 시 as_of 를 갱신하고 CHANGELOG 에 남길 것.

금액 단위: 만원.
"""

# ───────────────── 주택임대차보호법 — 소액임차인 최우선변제 (청주 = '그 밖의 지역') ─────────────────
# 적용 기준일은 '최초 담보물권(근저당 등) 설정일'이다. 계약일이 아님 — 설정일이 속한 구간의 표가 적용된다.
# 출처: 주택임대차보호법 시행령 제10·11조. 최우선변제액은 주택가액(경매 등)의 1/2 범위 내에서만 인정.
SOAK_TABLE_ETC = [  # 그 밖의 지역(청주시 포함) — [적용 시작일, 소액보증금 상한(만원), 최우선변제액(만원)]
    {"from": "2023-02-21", "deposit_max": 7500, "protected": 2500},
    {"from": "2021-05-11", "deposit_max": 6000, "protected": 2000},
    {"from": "2016-03-31", "deposit_max": 5000, "protected": 1700},
]
SOAK_NOTE = ("적용 구간은 계약일이 아니라 등기부상 '최초 담보물권(근저당 등) 설정일' 기준입니다. "
             "최우선변제액은 주택가액의 2분의 1 범위 내에서만 인정됩니다. "
             "최신 개정 여부는 법제처(law.go.kr)에서 확인하세요.")
SOAK_AS_OF = "2023-02-21 시행 시행령 기준"
SOAK_SOURCE_URL = "https://www.law.go.kr/법령/주택임대차보호법시행령"

# ───────────────── HUG 전세보증금반환보증 — 핵심 요건(아파트·비수도권 기준) ─────────────────
# 출처: 주택도시보증공사(HUG) 공시 상품 요건. 세부 요건·서류는 심사에서 확정 — '요건 충족 여부'만 안내.
HUG_RULES = {
    "as_of": "2025년 HUG 공시 기준(변동 가능)",
    "official_url": "https://www.khug.or.kr",
    "items": [
        {"key": "deposit_cap", "label": "보증금 5억원 이하(비수도권)", "value": 50000,
         "note": "수도권은 7억원 이하."},
        {"key": "jeonse_ratio", "label": "보증금 ≤ 주택가격의 90%", "value": 90,
         "note": "주택가격은 HUG 산정 기준(공시가격 등) — 앱 시세와 다를 수 있어요."},
        {"key": "senior_debt", "label": "선순위채권 ≤ 주택가격의 60%", "value": 60,
         "note": "선순위채권(근저당 등)과 보증금의 합도 주택가격의 90% 이내여야 해요."},
        {"key": "no_seizure", "label": "권리침해(경매·압류·가압류·가처분) 없음", "value": None,
         "note": "등기부 갑구·을구에서 확인."},
        {"key": "move_in", "label": "전입신고 + 확정일자", "value": None,
         "note": "잔금·이사 당일 처리 권장."},
        {"key": "deadline", "label": "계약기간 1/2 경과 전 신청", "value": None,
         "note": "갱신계약도 갱신 기간의 1/2 경과 전."},
    ],
}

# ───────────────── 정책대출(주택도시기금·HF) — 청주(비수도권) 기준 요건 ─────────────────
# 출처: 주택도시기금(nhuf.molit.go.kr)·한국주택금융공사(hf.go.kr) 공고. 금액 만원.
# 요건 필드: income_max(부부합산 연소득), price_max(주택가/보증금 상한), limit(대출 한도), homeless(무주택 요구)
POLICY_AS_OF = "2025년 공고 기준(공고마다 변동 — 신청 전 공식 확인 필수)"
POLICY_PRODUCTS = [
    {
        "key": "didimdol", "name": "디딤돌 대출", "purpose": "buy",
        "desc": "무주택 실수요자 주택 구입 — 시중은행보다 낮은 기금 금리",
        "income_max": 6000, "income_max_newlywed": 8500, "income_max_kids2": 7000,
        "price_max": 50000, "price_max_boost": 60000,   # 신혼·2자녀 이상 6억
        "limit": 25000, "limit_boost": 40000,
        "homeless": True,
        "extra": "전용 85㎡ 이하(읍·면 100㎡). LTV 최대 70%.",
        "official_url": "https://nhuf.molit.go.kr",
    },
    {
        "key": "beotimmok", "name": "버팀목 전세자금", "purpose": "jeonse",
        "desc": "무주택 세대주 전세보증금 대출(비수도권 기준)",
        "income_max": 5000, "income_max_newlywed": 7500, "income_max_kids2": 6000,
        "price_max": 20000, "price_max_boost": 30000,   # 신혼·2자녀 이상 3억(비수도권)
        "limit": 8000, "limit_boost": 20000,
        "homeless": True,
        "extra": "청년(만 19~34세) 전용 버팀목은 보증금 3억 이하·한도 2억(요건 상이 — 공고 확인).",
        "official_url": "https://nhuf.molit.go.kr",
    },
    {
        "key": "bogeumjari", "name": "보금자리론", "purpose": "buy",
        "desc": "고정금리 장기 주택담보대출(HF)",
        "income_max": 7000, "income_max_newlywed": 8500, "income_max_kids2": 10000,
        "price_max": 60000, "price_max_boost": 60000,
        "limit": 36000, "limit_boost": 42000,           # 생애최초 한도·LTV 우대
        "homeless": False,
        "extra": "생애최초는 LTV 최대 80%. 무주택 또는 처분조건 1주택.",
        "official_url": "https://www.hf.go.kr",
    },
    {
        "key": "newborn", "name": "신생아 특례대출", "purpose": "both",
        "desc": "대출신청일 기준 2년 내 출산(2023.1.1 이후 출생) 가구 — 구입·전세 모두",
        "income_max": 13000, "income_max_newlywed": 13000, "income_max_kids2": 13000,
        "price_max": 90000, "price_max_boost": 90000,   # 구입: 주택가 9억 이하
        "price_max_jeonse": 40000,                       # 전세: 보증금 4억(비수도권)
        "limit": 50000, "limit_boost": 50000,            # 구입 한도 5억
        "limit_jeonse": 30000,
        "homeless": True,
        "extra": "소득 상한 완화(맞벌이 2억)가 발표된 바 있어 공고 확인 필수. 자산 기준 별도.",
        "official_url": "https://nhuf.molit.go.kr",
    },
]
POLICY_DISCLAIMER = ("요건 충족 '가능성' 안내이며 대출 승인·한도를 보장하지 않습니다. "
                     "소득·자산·주택 요건과 금리는 공고마다 바뀌므로 신청 전 반드시 공식 사이트에서 확인하세요. "
                     "청집사는 어떤 금융회사와도 제휴·수수료 관계가 없습니다.")

# 은행 공식 사이트(주담대·전세대출 안내 페이지가 아닌 최상위 도메인 — 개편에 강함, 수수료·제휴 0)
BANK_LINKS = [
    ("국민은행", "https://www.kbstar.com"),
    ("신한은행", "https://www.shinhan.com"),
    ("우리은행", "https://www.wooribank.com"),
    ("하나은행", "https://www.kebhana.com"),
    ("농협은행", "https://banking.nonghyup.com"),
    ("기업은행", "https://www.ibk.co.kr"),
    ("카카오뱅크", "https://www.kakaobank.com"),
    ("케이뱅크", "https://www.kbanknow.com"),
]
