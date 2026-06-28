"""
홈 피드 예시(placeholder) 데이터.

⚠️ 청약·분양·뉴스·정책은 실데이터 소스가 M4 단계(청약홈 API·네이버 뉴스 API·
   국토부/청주시 공지)에서 연동된다. 아래는 화면 구조 검증용 '예시'이며 실제 정보가 아니다.
   모든 항목 is_sample=True 로 내려가 UI 에서 '예시' 배지로 구분된다.
   (지침서: 뉴스 원문 전재 금지 → 제목·짧은요약·출처링크만. 여기 텍스트는 자체 작성 예시.)
"""

SUBSCRIPTIONS = [
    {"name": "[예시] 청주 OO지구 1단지", "location": "청주시 흥덕구",
     "period": "2025-12-01 ~ 12-03", "units": 480, "price": "최고 5.2억",
     "status": "접수예정", "competition_range": None, "min_score": None,
     "house_types": [
        {"type": "84A", "units": 220, "price": "4.9억", "competition": None, "min_score": None, "avg_score": None},
        {"type": "84B", "units": 180, "price": "5.0억", "competition": None, "min_score": None, "avg_score": None},
        {"type": "101", "units": 80, "price": "5.2억", "competition": None, "min_score": None, "avg_score": None}],
     "is_sample": True},
    {"name": "[예시] 청주 OO지구 2단지", "location": "청주시 청원구",
     "period": "2025-11-18 ~ 11-20", "units": 320, "price": "최고 4.1억",
     "status": "접수중", "competition_range": [3.2, 18.5], "min_score": 54,
     "house_types": [
        {"type": "59", "units": 120, "price": "2.9억", "competition": "18.5:1", "min_score": 62, "avg_score": 68},
        {"type": "84", "units": 200, "price": "4.1억", "competition": "3.2:1", "min_score": 54, "avg_score": 59}],
     "is_sample": True},
    {"name": "[예시] OO오피스텔", "location": "청주시 서원구",
     "period": "2025-11-05 ~ 11-06", "units": 150, "price": "최고 1.8억",
     "status": "마감", "competition_range": [1.1, 2.3], "min_score": None,
     "house_types": [
        {"type": "전용 24", "units": 90, "price": "1.2억", "competition": "1.1:1", "min_score": None, "avg_score": None},
        {"type": "전용 33", "units": 60, "price": "1.8억", "competition": "2.3:1", "min_score": None, "avg_score": None}],
     "is_sample": True},
]

NEWS = [
    {"title": "[예시] 청주 아파트 거래량, 전월 대비 변동", "source": "예시뉴스",
     "date": "2025-11-14", "url": "#", "category": "뉴스", "is_sample": True},
    {"title": "[예시] 흥덕구 신규 분양 일정 공개", "source": "예시뉴스",
     "date": "2025-11-12", "url": "#", "category": "뉴스", "is_sample": True},
    {"title": "[예시] 청주 전세가율 동향", "source": "예시뉴스",
     "date": "2025-11-10", "url": "#", "category": "뉴스", "is_sample": True},
]

POLICIES = [
    {"title": "[예시] 생애최초 주택구입 지원 안내", "summary": "대상·한도·신청 방법 요약(예시).",
     "source": "국토교통부(예시)", "date": "2025-11-01", "is_sample": True},
    {"title": "[예시] 디딤돌·보금자리론 금리 안내", "summary": "정책대출 금리·자격 요건 요약(예시).",
     "source": "한국주택금융공사(예시)", "date": "2025-10-28", "is_sample": True},
]
