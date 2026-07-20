# 개발 지침 (skills) — 청주 부동산 플랫폼

이 폴더는 이 프로젝트를 **유지·확장**할 때 따라야 할 개발 지침 모음입니다.
새 기능을 추가하거나 다른 개발자/LLM가 이어받을 때 **먼저 이 문서들을 읽으세요.**

## 절대 원칙 (모든 작업 공통)
1. **왜곡 없음(No Distortion)**: API 필드·수치를 추측해 채우지 않는다. 없는 값은 `null`/"표본 부족"으로 둔다. 예시·모의 데이터는 항상 `is_sample`/배지로 구분.
2. **공식 소스만**: 3장 공공 API·정식 제휴만 사용. 타 서비스 스크래핑 금지(부록 C).
3. **참고용 고지**: 실거래·대출·세금은 "참고용 추정치" 표기. 금융/세무 자문 아님.
4. **개인정보 최소**: 기본은 익명 `device_id`. 민감정보(소득·신용)는 동의·암호화·격리(지침서 9.A).
5. **설정값 분리**: 규제·요율(LTV/DSR/취득세/중개보수)은 코드 하드코딩 금지 → `*_RULES` 설정으로.
6. **확장 대비**: 신규 지역·유형은 코드/설정 추가만으로 되게(하드코딩 금지).
7. **문서 동기화(필수)**: 기능·패턴·스키마를 바꾸면 **같은 작업에서** 관련 `skills/*.md`·`ROADMAP.md`(진행 SSOT)·`CLAUDE.md`·`OPERATIONS.md`·`CHANGELOG.md`를 갱신한다. 문서가 코드보다 뒤처지면 이 폴더의 목적이 무너진다. "코드 짰으면 문서도 짠 것"으로 간주.

## 레포 지도
```
app/
  main.py            FastAPI 앱 + 라우터 등록 + UI 서빙(/, /sw.js) + Sentry init
  core/              config(키·규제값·캐시TTL) / cache(stat_cached) / logging / ratelimit
  data/              region_codes(4개 구), sample_feed(예시)
  models/__init__.py ORM: Region·Complex·Transaction·Favorite·UserPref·RecentView·SavedSearch
                     ·Account·DeviceLink·Listing·Post·Comment·PostLike·ReportLog·Notification
                     ·Bookmark·CommuteDestination·CommuteTime·PushSubscription·JobRun
  sources/           외부 커넥터: molit/ applyhome news finlife hf poi geocode kapt
  services/          stats(집계·price_overview) loan costs poi geocode living(생활권)
                     commute notify_transactions(+푸시) push monitoring enrich gongsi storage appmeta
  api/               dashboard home complex loan favorites personal auth listings search
                     admin community subscription commute price push (+notif_router)
  web/index.html     단일 React UI(DEMO 폴백, SheetShell 통일)   web/sw.js  웹푸시 SW
  fixtures/          오프라인 검증용 표본
scripts/  run_collect verify_region_codes geocode scheduler db_upgrade compute_commute
          seed_commute import_gongsi enrich gen_vapid backup restore doctor
migrations/  Alembic 0001→0019 (head 0019_post_resident, env.py가 앱 설정 URL 사용)
run.py    원클릭 실행      skills/  ← 본 지침 모음
```

## 작업 후 필수 검증 루틴 (UI 수정 시)
1. `<script type="text/babel">` 블록 괄호 균형 검사 `() {} []`.
2. 미정의 컴포넌트 스캔(`<Xxx` 중 정의 안 된 것 0개).
3. 백엔드 변경 시 `python -m py_compile`.
4. `app/web/index.html` → `outputs/cheongju-ui.html` 복사, `__pycache__`/`*.db` 제거 후 재압축.
> 샌드박스는 네트워크가 없어 외부 호출은 미검증. 로직/문법/계산만 오프라인 검증하고,
> 외부 응답 필드는 "Swagger 확인" 주석으로 남긴다.

## 문서 맵
- `data-and-sources.md` — 수집·정규화·커넥터 패턴
- `aggregations.md` — 집계(stats) 규칙
- `loan-costs.md` — 대출·세금 계산
- `personalization.md` — 개인화(기기 기반→로그인)
- `auth-and-roles.md` — 소셜로그인·역할(user/agent)
- `community.md` — 게시판·댓글/대댓글·알림·스크랩·작성자·원자 카운터·포커스 규칙
- `testing.md` — 테스트·CI(pytest·격리·픽스처)
- `deploy-and-db.md` — SQLite↔PostgreSQL·Alembic 마이그레이션 일원화·배포
- `frontend.md` — UI 컨벤션(포커스 버그·단위·색·차트)
