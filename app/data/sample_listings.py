"""예시 매물(UGC) 시드 — 첫 실행 시 매물 탭이 비지 않도록.
모든 항목 is_sample=True 로 적재되어 UI 에서 '예시' 배지로 구분된다(실제 매물 아님).
컬럼명은 app.models.Listing 과 일치한다."""

SAMPLE_LISTINGS = [
    {
        "poster_role": "agent", "title": "가경아이파크 4단지 로열층 급매",
        "deal_type": "trade", "property_type": "apartment",
        "lawd_cd": "43113", "dong_name": "가경동", "complex_name": "가경아이파크 4단지",
        "exclusive_area": 84.9, "supply_area": 112.3, "floor": 15, "total_floor": 25,
        "rooms": 3, "baths": 2, "direction": "남향", "price": 46500,
        "maintenance_fee": 18, "maintenance_items": "청소·경비·승강기",
        "move_in_date": "즉시입주", "approval_date": "2019-03",
        "options": "냉장고,에어컨,붙박이장",
        "description": "남향 로열층, 채광 우수. 인근 초등학교 도보 5분. 단지 내 상가·주차 여유.",
        "photos": [], "agent_office": "가경공인중개사사무소", "agent_name": "홍길동",
        "agent_reg_no": "43113-2024-00012", "agent_phone": "043-000-0000",
        "agent_address": "청주시 흥덕구 가경로 00",
    },
    {
        "poster_role": "user", "title": "복대동 신축 오피스텔 월세 (개인 직거래)",
        "deal_type": "wolse", "property_type": "officetel",
        "lawd_cd": "43113", "dong_name": "복대동", "complex_name": None,
        "exclusive_area": 23.1, "supply_area": 43.0, "floor": 7, "total_floor": 15,
        "rooms": 1, "baths": 1, "direction": "동향",
        "deposit": 1000, "monthly_rent": 55, "maintenance_fee": 7,
        "maintenance_items": "인터넷·수도 포함", "move_in_date": "2026-07-01",
        "approval_date": "2022-05", "options": "풀옵션",
        "description": "역세권 풀옵션 원룸형. 직거래 환영합니다.",
        "photos": [], "agent_phone": "010-0000-0000",
    },
    {
        "poster_role": "agent", "title": "용암동 빌라 전세 · 주차가능",
        "deal_type": "jeonse", "property_type": "rowhouse",
        "lawd_cd": "43111", "dong_name": "용암동", "complex_name": None,
        "exclusive_area": 59.8, "supply_area": 72.0, "floor": 2, "total_floor": 4,
        "rooms": 3, "baths": 1, "direction": "남동향", "price": 16500,
        "maintenance_fee": 5, "move_in_date": "협의", "approval_date": "2015-08",
        "options": "가스레인지",
        "description": "조용한 주택가, 세대당 1주차 가능. 채광 양호.",
        "photos": [], "agent_office": "용암공인중개사사무소", "agent_name": "김중개",
        "agent_reg_no": "43111-2023-00077", "agent_phone": "043-111-1111",
        "agent_address": "청주시 상당구 용암로 00",
    },
]
