"""예시 게시글/댓글(is_sample) — 게시판이 비어있을 때 분위기 제공. 실제 사용자 글 아님."""
SAMPLE_POSTS = [
    {"category": "info", "nickname": "복대동주민", "lawd_cd": "43113",
     "title": "복대동 신축 입주장 분위기 공유합니다", "complex_name": "샘플리버뷰", "property_type": "apartment",
     "body": "최근 복대동 신축 단지 입주가 시작되면서 전세 매물이 늘어난 느낌입니다. "
             "실거래는 시세 탭에서 꼭 확인하시고, 직거래는 등기·계약 전 확인 필수예요.",
     "like_count": 6, "comment_count": 2, "views": 134},
    {"category": "qa", "nickname": "내집마련중", "lawd_cd": "43112",
     "title": "서원구 분평동 vs 산남동 실거주 어디가 나을까요?",
     "body": "둘 다 학군·교통 비슷해 보이는데 실거주 만족도가 궁금합니다. 조언 부탁드려요!",
     "like_count": 3, "comment_count": 1, "views": 88},
    {"category": "local", "nickname": "청주소식통", "lawd_cd": "43114",
     "title": "청원구 오창 쪽 개발 이슈 정리",
     "body": "오창 일대 교통·산업단지 관련 이야기가 많네요. 공식 발표 기준으로만 판단하시길 권합니다.",
     "like_count": 9, "comment_count": 0, "views": 210},
]
SAMPLE_COMMENTS = [
    {"post_idx": 0, "nickname": "전세찾는중", "body": "정보 감사합니다. 시세 탭이랑 같이 보니 도움돼요."},
    {"post_idx": 0, "nickname": "흥덕러", "body": "직거래 사기 조심하세요. 꼭 확인!"},
    {"post_idx": 1, "nickname": "분평동5년차", "body": "분평동은 학원가가 가까워 아이 키우기 좋아요."},
]
