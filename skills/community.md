# skills/community.md — 커뮤니티·알림 개발 지침

게시판·댓글·좋아요·신고·알림·스크랩·작성자 프로필의 규약. 구현은 `app/api/community.py`
(라우터 `router`=/community, `notif_router`=/notifications)와 모델
`Post/Comment/PostLike/ReportLog/Notification/Bookmark`.

## 데이터 모델
- `Post`: category(free|qa|info|deal|local)·title·body·lawd_cd(지역 태그)·**complex_name/property_type**(@단지 연결)·**images(JSON)**·views·like_count·comment_count·report_count·status(active|hidden)·is_sample.
- `Comment`: post_id·**parent_id(1단계 대댓글)**·body·report_count·status. 답글의 답글은 최상위로 평탄화.
- `PostLike`: uq(post_id, owner). `ReportLog`: uq(target_type, target_id, owner). `Bookmark`: uq(owner, post_id).
- `Notification`: account_id(수신자)·type(comment|reply)·post_id·comment_id·actor_nickname·message·is_read. 인덱스 (account_id, created_at)/(account_id, is_read).
- `owner` = 로그인 시 `acct:<id>`, 아니면 `device_id` (`_owner(acc, device_id)`).

## 절대 규칙
1. **카운터는 원자적 UPDATE**: views·like_count·comment_count·report_count를 `x=(x or 0)+1`로 갱신 금지.
   `db.execute(update(Post).where(...).values(views=func.coalesce(Post.views,0)+1))` 사용.
   좋아요 감소는 `case((coalesce>0, x-1), else_=0)`로 0 하한. like/report 카운트는 갱신 후 재조회로 정확값 반환.
2. **알림 생성**: 댓글 → 글 작성자, 답글 → 부모 댓글 작성자에게. **본인·중복 수신 제외**(`_notify`가 no-op 처리). 커밋은 호출부에서.
3. **신고 누적 자동숨김**: `report_count >= REPORT_HIDE(5)` 면 status='hidden'. 본인 글/댓글은 신고 불가(UI), 수정/삭제는 작성자만.
4. **참고용 고지**: 게시글은 사용자 의견 — 공식 정보 아님 배너 유지. 시세는 시세/소식 탭의 공식 데이터로 확인하도록 안내.
5. **@단지 연결**: 글에 complex_name+lawd_cd 있으면 상세에서 "단지 시세 보기" → 단지 상세로 이동. 연결은 통합검색(/search complexes)으로 선택.

## 프런트 함정 (반드시 지킬 것)
- 댓글/대댓글은 **컴포넌트가 아니라 렌더 함수 `renderCmt(c, reply)`**로 그린다.
  이유: JSX 안에서 `<Cmt/>`처럼 컴포넌트를 정의·사용하면 부모 state(입력값) 변경마다 리마운트되어
  **댓글/답글 입력창 포커스가 빠진다.** 렌더 함수는 같은 컴포넌트 트리에 인라인되어 포커스가 유지됨.
- 입력 상태(reply 텍스트·편집 텍스트)는 상위(PostDetail)에서 관리, key는 안정적인 id 사용.

## 엔드포인트 요약
- 글: `GET /community/posts`(category/gu/q/sort/mine/page) · `GET /best`(주간) · `GET /mine`(내 글·댓글) · `GET /posts/{id}`(liked/bookmarked 포함) · `POST /posts` · `PUT /posts/{id}`(수정) · `DELETE`.
- 댓글: `POST /posts/{id}/comments`(parent_id) · `PUT /comments/{id}` · `DELETE`.
- 반응: `POST /posts/{id}/like`(토글) · `POST /posts/{id}/report` · `POST /comments/{id}/report` · `POST /posts/{id}/bookmark`(토글) · `GET /bookmarks`.
- 작성자: `GET /community/authors/{account_id}`(글·통계·배지). 배지=글 수(새내기/회원/활발/베테랑).
- 알림: `GET /notifications`(열면 일괄 읽음) · `GET /notifications/unread_count`(헤더 벨 폴링) · `POST /notifications/read`.

## 향후
- 실시간 알림(현재 폴링 → SSE/WebSocket/푸시), 알림 타입 확대(좋아요/멘션), 작성자 팔로우, OFFSET→keyset 페이지네이션.


## 데이터 알림(관심 단지/지역 신규 실거래)
- services/notify_transactions.py 가 수집(live) 직후 실행. type="transaction" Notification 생성.
- 매칭 키는 프런트 favId 와 동일: 단지 `name__lawd__type`, 지역 `region:구명`.
- 멱등: app_meta.notify_last_tx_id 커서 이후만 처리. 수신자는 DeviceLink 로 account 연결된 사용자만.
- 알림 문구는 '건수+대상명'만(사실). 모의(is_sample)·해제(is_canceled) 제외.
- 프런트: NotificationsOverlay 가 transaction 이면 onOpenComplex 로 단지 상세 이동.


## 단지 주민 뱃지·단지 이야기 (v1.158)
- 작성 시 `_my_home_of(db, account_id)`(DeviceLink→UserPref.data.my_home)와 body.complex_name/lawd_cd 대조 → `Post.resident` 저장. 클라이언트가 resident를 보낼 수 없음(위조 방지).
- 라벨 정직성: '주민' = 우리집 자가 등록 기반(서류 인증 아님)임을 UI 툴팁·안내문에 명시. 후행 확장: 관리자 검증 시 verified 단계 추가 여지.
- 목록 필터 `GET /community/posts?complex=<단지명>` → 단지 상세 ComplexTalk가 사용.
