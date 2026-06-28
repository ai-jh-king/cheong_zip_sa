"""통근권 목적지 시드(청주 주요 직장·교통·공공·교육 거점).

⚠️ 좌표는 '근사값(seed_approx)'이다. 운영 시 scripts.seed_commute --geocode 로
   카카오 지오코딩(address 기반) 갱신 후 coord_method='geocoded' 로 승격 권장.
   통근시간 추정 자체가 근사이므로 근사 좌표도 사용 가능하되, 정확도 라벨을 노출한다.

category: transit(교통) / job(직장·산단) / public(공공) / education(교육) / medical(의료)
"""

COMMUTE_DESTINATIONS = [
    # 교통 거점
    {"key": "osong_ktx",      "name": "오송역(KTX)",       "category": "transit",
     "lat": 36.6207, "lng": 127.3271, "gu": "흥덕구", "address": "충북 청주시 흥덕구 오송읍 오송역로", "sort_order": 10},
    {"key": "cheongju_airport", "name": "청주국제공항",     "category": "transit",
     "lat": 36.7166, "lng": 127.4992, "gu": "청원구", "address": "충북 청주시 청원구 내수읍 오창대로", "sort_order": 40},
    {"key": "express_terminal", "name": "청주고속버스터미널", "category": "transit",
     "lat": 36.6330, "lng": 127.4290, "gu": "흥덕구", "address": "충북 청주시 흥덕구 가경동", "sort_order": 50},

    # 직장 · 산업단지
    {"key": "osong_bio",      "name": "오송 바이오단지",     "category": "job",
     "lat": 36.6310, "lng": 127.3290, "gu": "흥덕구", "address": "충북 청주시 흥덕구 오송읍", "sort_order": 20},
    {"key": "ochang_complex", "name": "오창 과학산업단지",   "category": "job",
     "lat": 36.7100, "lng": 127.4400, "gu": "청원구", "address": "충북 청주시 청원구 오창읍", "sort_order": 21},

    # 공공
    {"key": "city_hall",      "name": "청주시청",           "category": "public",
     "lat": 36.6424, "lng": 127.4890, "gu": "상당구", "address": "충북 청주시 상당구 상당로 155", "sort_order": 30},
    {"key": "province_office", "name": "충청북도청",         "category": "public",
     "lat": 36.6360, "lng": 127.4910, "gu": "상당구", "address": "충북 청주시 상당구 상당로 82", "sort_order": 31},

    # 교육
    {"key": "cbnu",           "name": "충북대학교",          "category": "education",
     "lat": 36.6296, "lng": 127.4565, "gu": "서원구", "address": "충북 청주시 서원구 충대로 1", "sort_order": 60},
]
