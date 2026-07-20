# 변경 이력 (CHANGELOG)

> 버전 표기: `vMAJOR_MINOR` (파일명) / `MAJOR.MINOR` (VERSION). 배포(전달)할 때마다 한 칸 올립니다.
> 규칙: 큰 기능/구조 변경=MAJOR, 기능 추가·개선=MINOR. 각 항목은 사용자 관점으로 간결히.

## v1.188 (2026-07-20) — 의존성 CVE 패치 + 운영 백업(pg_dump)
- **CVE 의존성 업그레이드**: `fastapi 0.115.0→0.115.6`(starlette 0.38→0.41, CVE-2024-47874 멀티파트 DoS 해소) · `python-multipart 0.0.9→0.0.18`(CVE-2024-53981 해소).
- **Dockerfile에 postgresql-client 설치** → `scripts/backup.py`의 `pg_dump`가 동작(과거 슬림 이미지에 미포함이라 **운영 PG 백업이 항상 실패**했음).
- 검증: verify_all PASS · pytest 154 · smoke_e2e 18(업그레이드된 fastapi/starlette로 회귀 없음).
## v1.187 (2026-07-20) — 대규모 서비스 대비 하드닝(보안·성능)
> 6축 전면 감사(성능·확장성·코드·보안·문서·기능) 후속. "많은 사용자 서비스" 관점의 P0 결함 처리.
**보안**
- **`AUTH_DEV_LOGIN=true` 프로덕션 부팅 거부**(인증 우회 백도어 차단). render.yaml `APP_ENV=production` 추가(이게 없으면 v1.178 가드 전부 무력이었음).
- **매물 목록에서 연락처·상세주소 제거**(_row_light) → 순번 ID 대량 스크래핑 PII 차단(상세 조회에선 유지).
- **미보호 쓰기 엔드포인트 레이트리밋 추가**: `/listings/upload`(디스크 DoS), `/me/prefs`·`/me/recent`·`/me/searches`(개인화 남용), `/push/*`, `/complex/quotes`. PUT 메서드도 `_rl_rule`이 처리하도록.
**성능(초기 로딩)**
- **집계 캐시 무효화를 DB(app_meta) 기반으로**: `data_version`을 DB에 저장 → **별도 컨테이너(cron) 수집의 bump가 웹 프로세스/다중 워커에 전파**(과거 인프로세스 int라 크론 bump가 웹에 안 보여, 캐시가 사실상 TTL로만 갱신 = "10분마다 콜드 재계산" 유발). 조회 폭주 방지 위해 30초 로컬 캐시.
- **`cache_ttl_stats_sec` 600→21600(6h)**: 1차 신선도는 data_version 무효화, TTL은 백스톱. "매 방문이 콜드" 해소.
- **`pricecheck` 3종(gu_context·bargain_radar·jeonse_risk_map)에 `@stat_cached`**: 매 요청 풀스캔 제거(CLAUDE.md 규약 위반 교정).
- **`/home/feed` 외부 API 3종 병렬화**: 청약·경쟁률·뉴스 직렬 호출(콜드 최악 34초)을 ThreadPoolExecutor로 병렬(최대값)로 단축. 첫 페인트 지연 완화.
**코드 건전성**
- **매물 조회수 원자화**: `x.views=(x.views or 0)+1` → `update(...).values(func.coalesce)`. 회귀 테스트 신설(test_listings.py).
- 테스트: 집계 캐시 프로세스 격리(conftest `_clean`에서 cache 초기화), pricecheck 캐시 무효화(_bump). pytest **154**(+2).
- 검증: verify_all PASS · pytest 154 · smoke_e2e 18.
## v1.186 (2026-07-20) — 단지 상세: 전체 평균 제거·면적별 통합
- **[상세] '단지 전체 최근 매매가'(평수 혼합 평균) 제거**: 평형 탭이 생겨 평수별로 볼 수 있으므로, 평수가 섞여 의미가 흐린 단지 전체 평균 큰 숫자·단지 추세·메트릭 그리드를 삭제. 전체 탭에서는 **면적 무관하게 유효한 '구 평균 대비 포지션' + 안내**만 슬림 스트립으로 남기고, 실제 시세는 **면적별 카드가 담당**(평형 탭과 완전 통합). 요약↔면적별 개념 중복 해소.
- 검증: verify_all PASS · pytest 152 · 브라우저 스모크(전체 평균 제거·구 대비 스트립·면적 카드, 콘솔 에러 0).
## v1.185 (2026-07-20) — 아이콘 SVG 전면 전환(콘텐츠 이모지 → Icon)
> UI 아이콘을 이모지 → SVG(Icon 컴포넌트)로 대거 통일. OS/폰트별 이모지 렌더 편차 제거, 톤 일관.
- **Icon 컴포넌트에 14종 신규**: compass·rocket·won·shield·megaphone·kids·factory·train·gov·hospital·pill·book·crown·flame.
- **홈 섹션/카드**: 우리집(home)·청주는 지금(rocket)·온보딩 배너(compass)·이 단지 한눈에(home + 칩 build/map/factory/academy/rocket).
- **홈 티커 라벨**: TickerBanner에 icon prop 추가 → 급매(bargain)·거래급상승(flame)·대장(crown). 이모지 제거.
- **더보기**: Quick(관심 star·청약 subscription·게시판 board)·Tool(통근 compass·예산 won·대출 loan)·전세안전(shield)·공식링크 헤더(search)·친구알리기(megaphone).
- **공식 링크 10종**: 등기부(doc)·건축물대장(build)·실거래(rank)·공시가격(won)·전세보증(shield)·금리(won)·임대차신고(doc)·세금(loan)·청약(subscription)·시청(gov).
- **단지 상세**: 육아환경(kids + kids/academy/hospital/book/sports/pill)·직장거점(factory + factory/train/gov/academy/hospital).
- **지도 핀**: 호재(🏗)·급매(📉)·전세위험(🏠)·통근거점(🏢) → 흰색 인라인 SVG.
- 남은 이모지(임장 🧭·검색 빈상태 🔎·일부 라벨 🔥·공유 텍스트 🏠·팁 💡)는 텍스트/플레이버로 유지.
- 검증: verify_all PASS · pytest 152 · 브라우저 스모크(홈 티커·더보기 도구/링크·상세 한눈에/육아/직장 SVG·콘솔 에러 0). 지도 핀은 로컬 네이버키 미등록으로 코드 검증(배포 도메인 정상).
## v1.184 (2026-07-20) — UI 크롬 아이콘 SVG 통일
- **[상단바] 메뉴(☰)·알림(🔔) → SVG**: 이모지 대신 Icon 컴포넌트(more/bell), 메뉴는 '청집사' 타이틀(18px)과 어울리게 size 21·INK 색. OS/폰트별 이모지 렌더 편차 제거.
- **[게시판] 게시판/매물 탭 → SVG**: 💬/🏠 → Icon board/listing(활성 INK·비활성 MUTED).
- **[게시판] 글쓰기 버튼**: "+ 글쓰기" → 연필(edit) SVG + '글쓰기', btn-primary 유지(테마 일관·흰 아이콘).
- **[설정] 푸시 알림 라벨 🔔 → SVG bell**. Icon 컴포넌트에 `color` prop(임의 색 지정)·`edit`(연필) 아이콘 추가.
- 남은 이모지(홈 카드·티커 라벨 등)는 콘텐츠 플레이버로 유지(후속 논의). 검증: verify_all PASS · pytest 152 · 브라우저 스모크(메뉴/탭/글쓰기 SVG·콘솔 에러 0).
## v1.183 (2026-07-20) — 홈 개인화 우선 재배치
- **[홈] 관심 단지(FavList)를 개인화 묶음으로 상단 이동**: 기존엔 급매·거래급상승·대장아파트 티커 3개 아래(9번)라 재방문 사용자가 자기 추적 단지를 보려면 한참 스크롤해야 했음. **우리집 → 최근 본 → 관심 단지** 로 개인 콘텐츠를 먼저 묶고, 시장 신호(호재·급매·거래급상승·대장)는 그 뒤로. "내 것 먼저, 시장 신호는 그다음" = 리텐션 정렬. 순서 변경만(로직·데이터 무변).
- 검증: verify_all PASS · pytest 152 · 브라우저 스모크(렌더 순서 확인·콘솔 에러 0).
## v1.182 (2026-07-19) — 지도 필터 SVG 아이콘 + 티커 정렬
- **[지도] 필터 토글을 이모지 → SVG 아이콘**: 학원·체육·생활·호재·급매·전세위험·현위치를 기존 `Icon` 컴포넌트(stroke 기반)로 통일(academy/sports/store/build/bargain/alerthome/locate 6종 신규). 활성 시 teal, 비활성 회색으로 상태 표시. OS·폰트별로 제각각이던 이모지 렌더 일관화.
- **[홈] 티커 숫자 정렬**: 급매/거래급상승/대장아파트 티커의 라벨 pill 폭을 통일(minWidth) → 순위 숫자 열이 세로로 정렬(기존엔 라벨 길이차로 어긋남).
- 검증: verify_all PASS · pytest 152 · 브라우저 스모크(SVG 아이콘 6종+현위치·활성 teal 전환·티커 숫자 열 정렬 524px, 콘솔 에러 0).
## v1.181 (2026-07-19) — 단지 상세 정보구조 정리(평형 탭 통합·지도 위치)
- **[상세] 단지 전체 요약 + 면적별 상세 통합**: 상단 평형 탭이 생겼으므로 둘을 합침. **전체 탭** = 단지 전체 요약 카드 + 각 면적 카드(접힘). **특정 평형 선택** = 그 평형의 상세(중앙값·평단가·적정가 체크·추이·최근 실거래·대출)를 상단에 바로 표시(단지 전체 요약은 중복이라 숨김). 하단에 따로 있던 '면적별 상세' 섹션 제거 = 스크롤·중복 감소.
- **[상세] 지도(위치)를 '이 단지 한눈에' 위로 이동**: 위치를 먼저 보고 동네 요약을 읽는 흐름으로.
- 순수 정보구조 개편(새 데이터·계산 없음). 검증: verify_all PASS · pytest 152 · **브라우저 실데이터 스모크**(전체/평형 탭 전환·요약↔면적 상세 통합·지도 순서·콘솔 에러 0).
## v1.180 (2026-07-19) — 판단 강화 3종(타겟 사용자 관점)
> "말릴 수 있는 앱"·전입자 창끝 관점의 부족분 보완. 원칙: **새 수치를 만들지 않고 이미 검증된 사실만 재구성/공간화** = 왜곡 없음.
- **[상세] 통합 주의 신호 카드(CautionSignals)**: 흩어져 있던 주의 사실(전세가율 높음·전고점 대비 급락·표본 적음·해제 거래)을 단지 상세 상단 한 장으로 통합. 판정("사지 마세요") 금지 = 사실+근거+면책, 신호 없으면 숨김(안전 암시 방지). 기존 신뢰도 콜아웃 흡수(중복 제거)·평형 탭 반응.
- **[지도] 전세가율 위험 핀(🏠 전세위험)**: 청주 최대 화두(갭투자·역전세)를 '판단이 얹힌 지도'에 공간화. `services/pricecheck.jeonse_risk_map`(전세보증금 중앙값÷매매가 중앙값, 매매·전세 각 3건+ 표본 게이팅·좌표 없으면 제외·역전세 단정 금지·면책, 단지 상세와 동일 산식) + `GET /pricecheck/jeonse-risk` + 지도 토글(급매 핀과 동일 패턴, high≥85 빨강/elevated 주황). 회귀 테스트 2건.
- **[상세] 동네 프로필(🏘 이 단지 한눈에)**: 전입자용 사실 digest — 연식(신축/준신축/구축)·구 평균 대비 시세·직장 직선거리·초품아·개발 호재 건수를 상단 칩으로. **'조용한 동네' 같은 주관 평가는 데이터에 없으므로 담지 않음**(왜곡 없음), 없는 사실은 칩 미생성.
- 검증: verify_all PASS · pytest **152**(+2) · smoke_e2e 18 · **브라우저 실데이터 스모크**(통합 주의 신호·동네 프로필 렌더 확인·콘솔 에러 0 / 전세위험 토글 fetch 200·엔드포인트 15건 확인). ⚠️ 전세위험·급매 핀의 '지도 위 시각' 확인은 로컬 네이버 지도 키 도메인(localhost 미등록)으로 불가 — 배포 도메인에선 정상(코드는 작동하는 급매 핀과 동일 패턴).
## v1.179 (2026-07-19) — 홈 정리 + 단지 상세 평형 탭 + 전세 위젯 통합
> 화면을 늘리지 않으면서 '알짜'만 남기는 방향. 홈 항목은 가치에 맞게 압축, 단지 상세는 평수 혼재를 평형 탭으로 해소.
- **[홈] 급매 → 압축 티커**: `📉 급매 포착`을 '거래 급상승'과 동일한 1줄 TickerBanner 패턴으로(BargainRadar 재작성). 한 건짜리 낮은 거래는 특수거래(직거래·가족)일 수 있어 실행 가능성이 제한적 → 큰 카드가 아니라 티커로 강등(지도 📉핀·단지 상세 적정가 체크가 주 노출). 펼치면 전체 목록(RankSheet).
- **[홈] 최고 상승·하락 카드 제거**: '직전 2건 비교'는 층·동·시점이 다른 거래를 비교해 가짜 급등락이 잦고(노이즈) 실행성이 낮아 홈에서 제거. 랭킹 탭(등락폭 순)에는 유지. → 홈이 오히려 짧아짐.
- **[단지 상세] 평형 탭 신설**: 상단에 `전체 / 24평 / 32평 …` 평형 탭. 선택 시 요약 카드(최근 매매가·전고점 대비·평단가)·시세 추이·면적별 상세·전세가율이 **그 평형 기준으로 전환**('단지 전체 최근 매매가'가 평수 뒤섞여 불명확하던 문제 해소). 기존 narrowed 로직 재사용, 외부 포커스(sel.area)와 호환.
- **[단지 상세] 면적별 상세 컴팩트화**: 전체 보기에서는 각 면적 카드를 접힌 상태로, 특정 평형 선택 시 펼침(화면 길이 절약).
- **[단지 상세] 전세가율+전세 안전도 통합**: 중복이던 `RentSignal`(전세가율 카드)을 `JeonseSafety`(안전도 게이지)에 흡수해 **하나의 위젯**으로. 게이지·비율·밴드·한줄 해석은 기본 노출(알짜), 계약 전 확인 체크리스트·보증기관(HUG/HF) 링크는 '계약 전 확인 ▾' 접이식. 평형 탭에 반응해 **선택 평형의 전세가율**을 표시(기존엔 단지 전체 고정).
- 검증: verify_all PASS · pytest 150 · smoke_e2e 18 · **브라우저 실데이터 스모크**(홈 급매 티커·최고상승하락 제거 확인 / 상세 평형 탭 전환·통합 전세 위젯·접이식, 콘솔 에러 0).
## v1.178 (2026-07-19) — 전면 감사 후속 조치(해자·운영 안정성·프런트 부채)
> 5축 병렬 코드·전략 감사(해자 신호·전입자 온보딩·주민 커뮤니티/판단 지도·데이터 격차·코드 건전성)에서 나온 실결함을 수정. 전략 정합성·왜곡없음 준수는 '강함/우수'로 확인됨.
- **[FIX·해자] 주민 뱃지 위조 벡터 차단**: `edit_post`가 `complex_name`/`lawd_cd` 변경 시 `Post.resident`를 재계산하지 않아, 우리집 단지로 뱃지 획득 후 다른 단지로 편집하면 🏠주민 뱃지가 유지되던 구멍. `resident` 산출을 모듈 헬퍼 `_compute_resident`로 추출해 create/edit 양쪽에서 서버 대조 → '위조 불가 주민 뱃지'(복리 해자)가 실제로 성립. 회귀 테스트 추가.
- **[FIX·원칙] 비원자 카운터 제거**: `delete_comment`의 `comment_count -= 1`(read-modify-write)을 `update(...).values(case(...))` 원자 감소로 교체(0 미만 방지). CLAUDE.md 명시 금지 규칙 준수. 회귀 테스트 추가.
- **[운영] 프로덕션 부팅 안전 가드**: `app_env=production`에서 **JWT_SECRET 미설정 시 부팅 거부**(다중 워커 간 임시키 불일치 → 간헐적 로그아웃 장애 예방). AUTH_DEV_LOGIN=true·CORS `*`는 경고 로그. `Settings.is_production` 프로퍼티 신설.
- **[전략·창끝] 통근 거점 자동 시드 안전망**: 부팅 시 job 거점 0건이면 `seed_commute` 자동 실행(멱등·좌표 하드코딩·API키 불필요). 시드 누락으로 **전입자 온보딩 위저드 1단계가 빈 목록**이 되던 사고를 구조적으로 차단. `auto_seed_commute` 플래그(테스트는 false).
- **[프런트 부채] 렌더 본문 내 컴포넌트 정리(§10 트랩#1)**: 순수 표시 컴포넌트 `Stat`·`Tool`·`Quick`를 모듈 레벨로 승격(호출부 불변), 부모 state를 잡는 `Chip`·`Tab`은 렌더 함수(`renderChip`/`renderTab`)로 변환 → 리마운트 churn 제거·입력 포커스 사고 잠복 지뢰 제거. `GU_NAME`/`GU_NAMES` 중복 정의 통합(키가 문자열로 강제되어 동작 동일).
- 검증: verify_all PASS · pytest **150**(+2) · smoke_e2e 18 · **브라우저 스모크**(게시판 칩/탭·더보기 Tool/Quick·지도, 콘솔 에러 0).
- 후속(태스크): 지도 POI 토글을 시설 데이터 미적재 시 숨김(시설 데이터 인프라와 함께), `Sel`/`Row` 이름충돌 순수쌍 정리(파일 분리 시).
## v1.177 (2026-06-28) — Claude Code 인수인계 문서화
- **`HANDOFF_TO_CLAUDE_CODE.md` 신설** — 웹 Claude에서 Claude Code 환경으로 옮기면서 새 Claude가 처음 읽어야 할 최상단 인수인계서.
  - 사용자 절대 원칙(왜곡 없음·인수인계 문서·step by step·대규모 대비·먼저 파악해 제안·최신 UI·실제 앱 테스트·서비스 단계 실수 금지) 명문화.
  - 3층 해자 전략, 메인 기능 결정('판단이 얹힌 지도'), 완비 기능/데이터 대기 기능/알려진 부채 스냅샷.
  - 진행 중이던 카카오 KOE101 미완 상태 + 다음 큰 작업(PostgreSQL 전환) 명시.
  - Claude Code 환경 첫 실행 절차, 검증 3층 루틴, 코드 구조·문서 위계, 릴리스 규율·패키징 관례, 커뮤니케이션 스타일, 정적 검사가 못 잡았던 사고 5건 교훈 정리.
- ROADMAP 스냅샷: v1.176으로 갱신, 인수인계 사실 표시.
- 검증: verify_all PASS · pytest 148 · smoke_e2e 18. (문서만 추가, 코드 무변경)
## v1.176 (2026-06-28) — 소셜 로그인 콜백 진단성·안정성 강화
- **[FIX] 조용한 KeyError → 원인 표면화**: `_exchange_and_profile` 가 `tok["access_token"]`·`me["id"]` 를 직접 인덱싱해 실패 시 KeyError → 조용히 `?login=error` 리다이렉트 → **원인 진단 불가**. `.get()` + 상세 `RuntimeError("<provider> token 실패: ...")` 로 개편.
- **[진단] 콜백 실패 사유 로그·URL 노출**: 콜백에서 예외 발생 시 `auth.oauth` 로거에 스택 남기고, 리다이렉트 URL 에 `?login=error&provider=<p>&why=<짧은 사유>` 붙임(시크릿 없음). 사용자·개발자 둘 다 원인 즉시 확인 가능.
- **[FIX] 카카오 Client Secret 지원**: 카카오 콘솔 '보안 > Client Secret 사용' ON 한 앱은 토큰 교환 시 secret 필수인데 기존 코드가 안 보냄 → 실패. `KAKAO_LOGIN_CLIENT_SECRET` env(선택) 추가, 설정 시에만 전송. OFF 앱이면 비워두면 됨.
- `SOCIAL_LOGIN_DEBUG.md` §7 로컬 진단 절차 추가(카카오 동의항목·네이버 사용 API 활성화 등 실제 원인 매핑).
- 검증: verify_all PASS · pytest 148 · smoke_e2e 18.
## v1.175 (2026-06-28) — 소셜 로그인(카카오·네이버) 진단·수정
- **[FIX] OAuth redirect_uri·state URL 인코딩 부재**: `app/api/auth.py` `/login/{provider}` 가 `redirect_uri=<https URL>` 을 미인코딩 raw 로 붙였음(카카오·네이버 모두 문자 단위 일치 요구 — 미인코딩 시 KOE006·redirect_uri_mismatch 유발 가능성). `urllib.parse.quote(safe="")` 로 감쌈. 실제 부팅해 URL 확인(`redirect_uri=https%3A%2F%2F...`) 정상.
- **[진단 문서] `SOCIAL_LOGIN_DEBUG.md` 신설** — ①필수 env 5종(AUTH_REDIRECT_BASE·KAKAO_LOGIN_REST_KEY·NAVER_LOGIN_CLIENT_ID/SECRET·JWT_SECRET) + `/auth/config` 확인 ②콘솔 리다이렉트 URI 문자 단위 일치(카카오 로그인 활성화·REST 키 / 네이버 서비스URL·CallbackURL) ③프런트 alert 문구별 원인 ④콜백 에러 코드 매핑(KOE006·KOE101·unauthorized_client) ⑤Shell 격리 테스트 ⑥임시 우회.
- 검증: verify_all PASS · pytest 148 · smoke_e2e 18 · 실앱 부팅으로 인코딩 URL 육안 확인.
## v1.174 (2026-06-28) — 🚨 지도 탭 크래시 긴급 수정(useRef 누락)
- **[FIX] 지도 탭 진입 시 화면 크래시**: v1.169에서 지도 개선(급매핀·현위치) 배선 시 MapHub 안 `useRef(null)` 호출을 추가했으나, 파일 상단 `const {useState,useEffect,useMemo,useCallback} = React;` 에 **`useRef` 구조분해를 안 넣음**. 지도 탭 진입 순간 ReferenceError → 화면 크래시. `useRef` 추가로 즉시 해소.
- **[예방] `scripts/verify_frontend`에 'React 훅 import/구조분해 정합' 검사 추가** — 파일에서 호출된 훅(useState/useEffect/useMemo/useCallback/**useRef**/useReducer/useContext/useLayoutEffect/useTransition)이 import 또는 React 구조분해로 실제 들어와 있는지 대조. 오프라인 검사(괄호·구문)가 못 잡는 '런타임 ReferenceError로 화면 크래시' 유형 영구 차단. 자가 테스트로 검증기 자체 동작 확인. verify_all 게이트에 자동 포함.
- 검증: verify_all PASS · pytest 148 · smoke_e2e 18.
## v1.173 (2026-06-28) — 더보기 '🛡 전세 안전 진단'(앱 내 상세 제공, 단순 링크 아님)
- **깡통전세 계산기(JeonseGuard)**: 매매 시세·전세 보증금·등기부(을구) 근저당 채권최고액 입력 → **(보증금+선순위)÷시세 비율**을 밴드로 진단(≥80% 위험 신호/70~80 주의/<70 상대적 여유) + 보증보험·특약 행동 안내. 계산식·'채권최고액=통상 원금의 110~130%' 설명, **단정 금지 면책**(경매 배당·법적 판단 아님). 외부 링크(등기부)와 "떼서 이 숫자를 넣으세요"로 연결되는 구조.
- **전세 계약 단계별 체크리스트**(접이식): 계약 전(등기부·건축물대장·전세가율·임대인 체납 열람)/계약일(당일 재발급·임대인 계좌·특약)/잔금·입주(재확인·전입신고+확정일자·보증보험) — 검증된 일반 절차만, '법률 자문 아님' 고지.
- **[사고 차단] 이름 충돌**: 기존 단지 상세 전세가율 게이지 `JeonseSafety`와 중복 정의 발생 → 새 컴포넌트 `JeonseGuard` 개명. **verify_frontend에 '최상위 함수 중복 정의 탐지' 추가**(재정의가 앞 정의를 덮어써 기존 화면 오동작하는 유형 영구 차단).
- 검증: verify_all(중복검사 포함) PASS · pytest 148 · smoke_e2e 18.
## v1.172 (2026-06-28) — '계약 전 꼭 확인' 외부 공식 링크 확장(7→10종)
- 추가: **💰 대출·예금 금리 비교**(금융감독원 금융상품 통합비교공시 finlife.fss.or.kr — 앱 대출계산기의 실제 금리 확인처) · **🧾 임대차(전월세) 신고**(국토부 rtms.molit.go.kr) · **🏦 취득·양도세 신고**(홈택스 — 앱 세금 계산기와 연결).
- 안심전세는 별도 안정 도메인 불확실 → 추측 URL 대신 HUG 항목 설명에 병기(왜곡 없음).
- 검증: verify_all PASS · pytest 148 · smoke_e2e 18.
## v1.171 (2026-06-28) — 더보기 '계약 전 꼭 확인'(공식 외부 서비스)
- **감사**: 앱이 데이터로 못 주는 계약 필수 확인 4종(등기부등본·건축물대장·실거래 원본·공시가격) 안내 부재 확인(기존은 청약홈·HF·HUG만).
- **더보기에 `OfficialLinks` 신설**: 등기부등본(인터넷등기소)·건축물대장(정부24)·실거래가 공개시스템(국토부)·공시가격 알리미·전세보증(HUG)·청약홈·청주시청 — 7개 공식 서비스 바로가기. "청집사가 대신 확인해줄 수 없는 것" 프레이밍으로 '말릴 수 있는 앱' 정체성 강화 + 기관 무관·무수익 고지.
- 왜곡 없음: 공식 최상위 도메인만 링크(하위 경로 하드코딩 금지 — 사이트 개편에도 안전). 새 데이터 생성 없음.
- 검증: verify_all PASS · pytest 148 · smoke_e2e 18.
## v1.170 (2026-06-28) — 유입(바이럴) 장치 3종
- **감사**: 더보기·프로필·공유·SEO를 점검 — 시세 카드 공유·SEO 랜딩은 있으나 **공유물에 앱 이름/주소가 없어 확산이 유입으로 연결 안 되는 구멍** 확인(ROADMAP 백로그와 일치).
- ① **공유 카드 워터마크**: 캔버스 하단 "🏠 청집사 — 청주 부동산을 한눈에" + 접속 도메인(location.host, 배포 도메인 자동 반영). 카톡방 확산→유입 연결.
- ② **호가검증 결과 공유**: '📤 이 결과 공유하기' — "『단지』 호가 X억, 중앙값 대비 +N%·이하 거래 P%" + 면책 + 링크. navigator.share→클립보드 폴백. **킬러 시그널이 퍼지는 형태**.
- ③ **더보기 '📣 친구에게 청집사 알리기'**: 중개·광고 없음 정체성 문구 + 링크 공유(전입 지인 타깃).
- 검증: verify_all PASS · pytest 148 · smoke_e2e 18.
## v1.169 (2026-06-28) — 메인 기능 결정: '판단이 얹힌 지도' + 지도 편의 개선
- **[전략 결정] 메인 기능 = 지도, 단 '판단이 얹힌 지도'** — 유입·체류는 지도(부동산 앱의 첫 본능), 차별화는 지도 위 우리만의 시그널('말릴 수 있는 앱'). CLAUDE 8.0·ROADMAP 명문화.
- **📉 급매 핀 레이어(지도)**: 급매 레이더를 홈 카드에서 지도 토글로 확장. `bargain_radar` 응답에 단지 좌표 포함(Complex 조인, 미지오코딩=None→핀 제외·왜곡 없음). 지도 필터에 '📉 급매' 토글(호재와 동일 레이어 패턴), 핀=파랑 배지(−N%), 클릭→단지 상세. 툴팁에 '사유 있을 수 있음' 고지.
- **📍 현 위치 버튼**: 지도 우하단 플로팅. geolocation→setCenter+줌15, 권한 거부/실패 시 안내(왜곡 없이 실패 고지). PriceMarkerMap `onMapReady`로 지도 인스턴스 노출.
- 테스트: 급매 좌표 포함 pytest 1건 추가(148 passed) + e2e에 좌표 체크(18 PASS). 문서: CLAUDE·ROADMAP·skills/frontend.
- 검증: verify_all PASS · pytest 148 · smoke_e2e 18.
## v1.168 (2026-06-28) — 앱(스토어) 배포 준비: Capacitor 스캐폴딩
- **"앱으로 배포하려면?" 실행 준비 완료**(웹은 이미 PWA로 설치형 배포 가능).
  - `frontend/capacitor.config.json` 신설(appId `com.cheongzipsa.app`, appName 청집사, webDir dist, 스플래시/스킴 설정).
  - `package.json`에 Capacitor 의존성(@capacitor/core·cli·android·ios·app·status-bar·splash-screen) + 스크립트(cap:sync=build&sync, cap:add:android/ios) 추가. version 1.168.
  - **`MOBILE_DEPLOY.md` 신설** — 실행 런북: ①PWA 즉시 배포(스토어 불필요) ②Android(cap add/sync/open→Android Studio 서명·AAB→Play) ③iOS(Mac+Xcode→TestFlight) ④필수 3설정(**VITE_API_BASE 절대주소·CORS capacitor origin·네이버 지도 도메인 등록**) ⑤심사 컴플라이언스 ⑥업데이트 운영.
  - `MOBILE_APP_STRATEGY.md` 낡은 '출발점' 현행화(A·B단계 done → 남은 건 C 네이티브 셸). ROADMAP·CLAUDE 반영.
  - 왜곡 없음: 네이티브 빌드·심사는 개발자 PC·스토어 계정에서 이뤄짐을 명시(저장소는 준비까지).
- 검증: verify_all PASS · pytest 147 · smoke_e2e 17.
## v1.167 (2026-06-28) — 전체 감사(전략·코드·방향성·서비스)
- **전면 감사 실시**(실코드+실구동): 확장성·성능·왜곡·서비스·문서 5축. 결과 `AUDIT.md` 신설.
  - 확장성: 지역코드 단일 소스 확인, 하드코딩 드리프트 없음(폴백·픽스처뿐). 사용자 경로 N+1 없음(.in_() 배치 검증). 캐싱 26함수.
  - 왜곡: 모의데이터 is_sample 격리 + 빈 DB에서 found=False/부족안내/면책 반환을 **실행으로 확인**(지어내지 않음).
  - 서비스: 배포 인프라·법적 고지 구비. 치명 리스크=운영 SQLite 시 데이터 소실 → PostgreSQL 필수(기존 문서화).
- **문서 인수인계 최신화**: ROADMAP 현재상태 스냅샷을 **v1.152→v1.166**으로 갱신(작동 기능·검증 3층·부채·우선순위). TESTING·DATA_PLACES 현행 주석. AUDIT.md 종합 판정+선결과제.
- 검증: verify_all PASS · pytest 147 · smoke_e2e 17. (코드 변경 없음 — 감사·문서)
## v1.166 (2026-06-28) — 실제 앱 구동 테스트로 실버그 2건 발견·수정
- 샌드박스에 런타임 의존성(fastapi·sqlalchemy·httpx 등) 설치에 성공 → **앱을 실제 부팅해 pytest(147개) + TestClient e2e 를 처음으로 실행**.
- **[FIX·중요] 전세가율 신호 왜곡** — v1.156 편집에서 `@stat_cached()` 데코레이터가 `complex_detail`→`rent_gap_signal` 로 **전이**됨. `stat_cached`는 첫 인자를 db로 간주(키 제외)하므로, `rent_gap_signal(jeonse_ratio)`가 **인자와 무관하게 첫 결과만 반환** → 모든 단지 전세가율 신호가 동일값이 되는 왜곡. 데코레이터를 원위치(complex_detail=캐시 필요)로 복원, rent_gap_signal은 순수함수로. pytest 147 all green.
- **[검증] 게시판 no such column·주민 뱃지** — 실제 구동에서 posts.resident 자가보강(_ensure_columns 모델 자동도출) 및 우리집 서버대조 resident=True 확인.
- **[신규] `scripts/smoke_e2e`** — TestClient 로 시세→단지상세(전세가율·추이)→호가검증→급매→게시판(주민)→온보딩 17종을 실데이터로 검증(전부 PASS). 검증 3층(정적/단위/통합) 체계를 TESTING.md 에 명문화. 데코레이터 전이 교훈 CLAUDE 기록.
- 검증: verify_all PASS · pytest 147 passed · smoke_e2e 17 PASS.
## v1.165 (2026-06-28) — 게시판 no such column·데이터 안 보임 진단·수정
- **[FIX] 게시판 `no such column: posts.resident`** — v1.158에서 추가한 `posts.resident` 컬럼이 SQLite 자가보강 목록(`_ensure_columns`)에서 누락됨 → SQLite 환경에서 컬럼 미생성.
  - **근본 해결**: `_ensure_columns`를 **모델(Base.metadata) 자동 도출식**으로 재작성. 앞으로 어떤 신규 컬럼도 SQLite 시작 시 자동 ALTER ADD(+boolean/int 0 백필) → 수동 목록 드리프트로 인한 'no such column' 재발 차단.
- **[진단] '데이터 전체 안 보임'** — `no such column`이 SQLite 고유 어투인 점에서, 운영이 **DATABASE_URL 미설정 → SQLite 폴백**으로 추정. SQLite 파일은 재배포 시 초기화(영속 디스크 없으면)되어 데이터 소실. 운영 해결책(PostgreSQL 연결 + db_upgrade + 수집/크론)을 OPERATIONS 7 '장애 대응'에 명문화. (코드가 아니라 운영 구성 이슈 — 왜곡 없이 원인 규명)
- 문서: OPERATIONS(장애 대응)·DATA(스키마 규칙)·CLAUDE 갱신. 검증: verify_all PASS.
## v1.164 (2026-06-28)
- **전달/배포 전 단일 정적 게이트 `scripts/verify_all` 신설 — 재발 방지 체계화**. '컴파일은 되는데 앱이 죽는' 사고를 전달 전에 반드시 차단.
  - `verify_imports` 강화: 기존 import 심볼 검사에 더해 **`module.attr` 접근 검증** 추가 — `stats.complex_detail(...)`처럼 호출부에서 없는 속성을 직접 잡음(이번 사고의 정확한 형태). 통제된 자가 테스트로 import 소실·속성 미정의 2종 모두 탐지 확인.
  - `verify_all` = compileall + verify_imports + verify_frontend 를 한 번에 실행하고 단일 PASS/FAIL. 라이브 검사(verify_region_codes=실제 MOLIT 호출)는 게이트에서 분리.
  - 문서화: 이 게이트를 **매 전달 전 필수**로 TESTING(최상단)·CLAUDE(검증 루틴)·OPERATIONS(배포 자가진단)에 명문화. 게이트가 못 잡는 범위(브라우저 스모크·pytest·라이브)도 명시.
  - 검증: verify_all PASS.
## v1.163 (2026-06-28) — 🚨 치명적 수정
- **[CRITICAL] `stats.complex_detail` 정의 소실 복구 — 앱 부팅 실패 버그**. v1.156에서 `rent_gap_signal`을 `complex_detail` 시그니처 앞에 삽입할 때 **`def complex_detail(...)` 줄이 유실**되어, 뒤따르는 본문이 `rent_gap_signal` 함수에 **흡수**됨(return 뒤 dead code라 문법은 정상 → compileall 통과). 결과: `complex_detail` 미정의 → 이를 import하는 `onboarding`(→main) 로드 시 **ImportError로 앱 전체 부팅 실패**, `/complex/detail`·landing도 사망.
  - 복구: `def complex_detail(...)` 시그니처+docstring 재삽입(본문·반환 rent_signal 온전). AST로 최상위 함수 확인, 타 함수 흡수 사고 없음 전수 확인.
  - onboarding의 미사용 import(rent_gap_signal·complex_detail) 정리.
- **[예방] `scripts/verify_imports` 신설** — 순수 AST로 `from app.X import a,b`의 심볼이 실제 정의됐는지 검증(서브모듈 허용). compileall이 못 잡는 두 사고(존재하지 않는 심볼 import=AGG_MONTHS / def 유실로 함수 흡수=complex_detail)를 **릴리스 전에 차단**. 릴리스 체크리스트·CLAUDE·skills/testing에 반영.
  - 검증: compileall·verify_imports·verify_frontend 모두 PASS.
## v1.162 (2026-06-28)
- **가격 검증 3종 — '말릴 수 있는 앱' 창끝 일괄 구현**(백엔드 services/pricecheck + /pricecheck/quote·gu-context·bargains, 프런트 3곳).
  - ① **호가 검증**(단지 상세 'PriceCheck'): 매물 호가(억) 입력 → 그 단지 최근 실거래 **중앙값 대비 %·이 가격 이하 거래 백분위**·건수·범위. 표본<3이면 부족 안내.
  - ② **분양 탭 '구별 기존 아파트 시세 맥락'**(GuContextBar): 분양가는 문자열·주택형 미확정이라 평단가 '판정' 대신 **비교 재료(구별 중앙값·평당가)** 를 나란히 제공(왜곡 없음 스코프 조정).
  - ③ **급매 레이더**(홈 BargainRadar): 같은 평형(round평) 12개월 중앙값 대비 **≤-12% 신고 실거래 사실** 나열(표본≥4에서만·저층/특수사정 고지). 탭 시 단지 상세.
  - 공통: 판정('적정/바가지/급매') 금지 — 위치·차이·사실 + disclaimer. 집계 윈도우=settings.aggregate_months.
  - 🛡 사전 차단한 사고: 존재하지 않는 stats.AGG_MONTHS import(컴파일 통과·**런타임 전체 다운**) 발견·수정 — 교훈을 skills/aggregations에 기록.
  - 테스트 3건(백분위·면책 / 레이더 임계·고지 / 구 맥락 중앙값). 문서: CLAUDE·ROADMAP·README·skills 갱신. 검증: compileall·verify_frontend PASS.
## v1.161 (2026-06-28)
- **전입자 온보딩 위저드 — 프런트(Step B) 완성**. 전략('사용자를 먼저 파악해 서비스 제안')의 첫 화면 구현.
  - `OnboardingWizard`: 전체화면 4단계(인트로→직장→예산→가족→결과), 진행 도트·큰 탭 타겟·한 화면 한 질문(모바일 우선 최신 트렌드), 하단 고정 `.btn-primary`. 결과 카드는 통근분·최근가(억)·전월대비·**예산 차액(자기자본 이내/+N 더 필요)** 표시, 탭 시 단지 상세로.
  - 진입: **첫 방문 1회 자동 안내**(스플래시 후 1.7s, safeStore `cj_onb_seen`) + 홈 배너(미완료 시) + 마이페이지 카드. 결과 저장 `UserPref.data.onboarding`(로그인 시 기기 동기화).
  - 왜곡 없음: 인트로·결과에 '중개·광고 없음 → 특정 매물 권유 안 함' 고지, 예산은 판정 아닌 차액, 데이터 없으면 안내.
  - 스코프 안전: OnbDots/OnbOption/Wizard 모듈 레벨, 의존 심볼(SkeletonList/Empty/Delta 등) 전역 확인. SkeletonList prop 정정.
  - 문서: CLAUDE·ROADMAP·skills/frontend 갱신. 검증: verify_frontend PASS.
## v1.160 (2026-06-28)
- **전략 실행: 전입자 온보딩 추천 — 백엔드(Step A)**. 포지셔닝('중개·광고 수익 0 → 말릴 수 있는 앱') + 신규 수요층(SK하이닉스·오송·오창 발령자)을 겨냥한 '청주가 처음이세요?' 큐레이션.
  - `services/onboarding.py` + `api/onboarding.py`(main 등록): `GET /onboarding/options`(직장·산단 = commute job 거점), `GET /onboarding/recommend?dest_key=&budget=&has_kids=&max_minutes=`.
  - **기존 부품 조립(새 데이터 생성 없음)**: search_by_commute(직장 근처 아파트) + complex_quotes(최근가·전월대비) + 예산 **차액(over_budget_by)**. 정렬=가격 있는 것 우선→통근 짧은 순.
  - **왜곡 없음**: 통근=직선거리 추정·매매가=중앙값(참고)·예산은 판정이 아닌 '차액'만. notice에 '특정 매물 권유하지 않음' 정체성 고지. 거점/데이터 없으면 빈 결과+안내.
  - 테스트 3건(옵션 목록·조립+정렬+차액·미지의 거점 안전). 프런트 위저드는 백로그(Step B).
  - 문서: CLAUDE(8.0 전략 포지셔닝 신설)·ROADMAP·README·skills/aggregations 갱신.
  - 검증: compileall·verify_frontend PASS.
## v1.159 (2026-06-28)
- **운영 데이터 자동 적재 설정** — "지금 실행하면 자동 적재인가?" 점검 결과(운영은 수동이었음) 해소.
  - `scripts/scheduler.py`에 **`--once` 모드**(크론용: 수집+지오코딩 1사이클 후 종료) + 지오코딩에 **시설(Place) 포함**(run_geocode_places 연동 — v1.154 신설분 스케줄러 누락 보완).
  - **render.yaml 크론 활성화**: `cheongju-collect`(매일 19:00 UTC=한국 04:00, `python -m scripts.scheduler --once`, DATABASE_URL/MOLIT/KAKAO env). 웹 plan을 실제 운영(starter)에 맞춤. Blueprint 미사용자(수동 배포)는 Apply 금지 경고 + 대시보드 Cron Job 생성 절차 안내.
  - OPERATIONS 3.1 개편(A. 대시보드 크론 생성 — 권장 / B. Blueprint / 확인법 last_collect_at·JobRun). ROADMAP 스냅샷 갱신.
  - 검증: compileall·verify_frontend·YAML 문법 PASS.
## v1.158 (2026-06-28)
- **전체 코드 점검(요청) 결과 및 조치**.
  - 확장성(충청도): 지역코드 단일 소스 `app/data/region_codes.py` 확인 — 구조 양호. 확장 시 수정 지점 5곳을 ROADMAP에 명문화(백엔드 4곳 + 프런트 GU_NAME/GU_NAMES 중복 → 통합 권장).
  - 불필요 기능: 미사용 `Sparkline` 컴포넌트 삭제. 숨김 시세탭·레거시 web/index.html은 폴백·부활용 의도적 유지로 판정.
- **🏠 아파트 인증 소통 — 단지 주민 뱃지 + 단지 이야기 (신규)**.
  - 백엔드: `posts.resident`(마이그레이션 **0019**). 글 작성 시 서버가 작성자의 '우리집(prefs.my_home, DeviceLink 경유)'과 @단지 태그를 **대조해 저장** — 클라이언트가 뱃지를 위조할 수 없음. `GET /community/posts?complex=` 단지 필터 추가. 직렬화(_post_light)에 resident 포함(목록·상세 공통).
  - 프런트: PostCard·PostSheet에 **🏠 주민 뱃지**(툴팁·안내로 "자가 등록 기반" 정직 표기 — 서류 인증 아님, 왜곡 없음). 단지 상세에 **💬 단지 이야기**(`ComplexTalk`, 해당 단지 최근 글 5건 + 참여 안내).
  - 후행 확장 여지: 관리자 서류 검증 시 verified 단계 승격(부록 B 원칙).
  - 테스트 1건 추가(주민 뱃지 서버 대조: 일치 True/불일치 False/단지 필터 — dev-login 패턴). 문서 6종 갱신(CLAUDE head 0019·ROADMAP 점검결론·README·DATA·skills/community·OPERATIONS).
  - 검증: compileall·verify_frontend PASS. 배포 시 `python -m scripts.db_upgrade` 필요(0019).
## v1.157 (2026-06-28)
- **지침서 2.3(시세 추이 & 등락폭 분석) 완비** — 단지 상세의 단순 스파크라인을 `TrendBlock`으로 교체.
  - **기간 토글 1년·3년·5년·전체**(데이터가 있는 옵션만 노출, 백엔드 timeseries=전체 이력이라 근거 있음).
  - **거래량 추이**: 가격 라인 아래 월별 거래건수 막대(X축 공유).
  - **전월 대비·전년 동월 대비 등락 칩**: 뷰 필터와 무관하게 전체 이력 기준으로 계산(정확성).
  - 다크 대응(var(--line)·MUTED), 라벨 자동 간격, "거래 있던 달 기준·소표본 주의" 문구(왜곡 없음). Sparkline 정의는 보존(미사용).
  - 전세가율(갭) 표시는 v1.156 RentSignal로 기이행. 지역(구) 추이 기간 토글은 백로그(홈 12개월 고정 유지, ROADMAP 기록).
  - 문서: ROADMAP·CLAUDE·skills/frontend 갱신. 검증: verify_frontend PASS.
## v1.156 (2026-06-28)
- **청주 특화: 전세가율/역전세 '신호' (RentSignal)** — 데이터로 검증된 청주 최대 화두(갭투자·역전세·양극화)에 대응. 단지 상세에 전세가율(전세 보증금 중앙값 ÷ 매매가 중앙값)을 **갭 크기·주의점**으로 해석한 카드 추가. 세입자·매수자·집주인 모두에게 유용한 맥락.
  - 백엔드 `stats.rent_gap_signal(jeonse_ratio)`: ≥85 high(갭 매우작음·역전세/깡통전세 주의·보증 확인 안내) / ≥75 elevated / ≥60 normal / <60 low. complex_detail 응답 `rent_signal`.
  - 프런트 `RentSignal` 카드(거래활발 옆): 전세가율 %·갭 뱃지·설명·**면책**(참고 지표, 가격 방향·역전세 단정 금지).
  - ⚠️ 왜곡 없음 철저: 예측·단정 표현 배제(테스트로 '반드시/확정' 금지 검증). 기존 jeonse_ratio 재사용 — 신규 데이터 지어내지 않음.
  - 테스트 1건 추가(밴드 경계·None·단정어 배제). 문서 갱신: CLAUDE·ROADMAP·README·skills/aggregations.
  - 검증: compileall·verify_frontend PASS.
## v1.155 (2026-06-28)
- **시설 API 엔드포인트 config 주입화(왜곡 없음)** — 체육·의료·도서관·어린이집 소스가 **추측 placeholder URL**(uddi:sports 등)을 하드코딩하던 것을, `.env` 설정값(`PLACES_SPORTS_URL`·`PLACES_MEDICAL_URL`·`PLACES_LIBRARY_URL`·`PLACES_DAYCARE_URL`)으로 전환. **미설정 시 수집 생략**(가짜 URL 호출 금지). config.py 필드·.env.example 추가.
  - 표준데이터 오픈API의 정확한 호출 URL(uddi UUID)은 활용신청 후 본인 API 페이지에만 노출되므로, 하드코딩 대신 주입 방식이 맞음(프로젝트 원칙: 외부 URL은 config).
  - **웹검증**: 전국어린이집표준데이터 = data.go.kr **15013108**(어린이집명·유형·운영현황·주소·정원수·현원수·위경도·놀이터수·CCTV 확인) → daycare 소스 데이터셋 ID 정정(기존 15059593 오기). 필드 매핑은 기존 tolerant 매핑이 검증 필드명을 이미 포함.
  - 문서: DATA_PLACES.md에 시설 엔드포인트 설정 방식·검증 데이터셋 표·설정 절차 추가.
  - 검증: compileall·verify_frontend PASS.
## v1.154 (2026-06-28)
- **시설 데이터 파이프라인 완비 — Place 지오코딩 추가(핵심 관문 해소)**. NEIS 학원 등 좌표 미제공 소스를 적재해도 좌표가 없어 지도·거리·육아·초품아에 안 뜨던 문제 해결.
  - `geocode.run_geocode_places()` 신설: 좌표 없는 Place를 **도로명주소 우선→명칭+동 폴백**으로 지오코딩(Kakao/Naver). 못 찾으면 None 유지(왜곡 없음). 변경 시 캐시 무효화.
  - `scripts/geocode.py`에 `places`·`all` 서브커맨드 추가(`python -m scripts.geocode places`).
  - **학원(NEIS) end-to-end 확립**: NEIS 키 → `collect_places academy` → `geocode places` → 육아환경·지도 학원 마커 활성. 절차·소량검증 권장은 DATA_PLACES.md.
  - 소스 검증 상태 명시(왜곡 없음): 학원(NEIS)·어린이집=검증 / 체육·의료·도서관=엔드포인트(uddi) 확정 대기.
  - 테스트 2건 추가(in_bounds bbox·카테고리 필터 / geocode 키 없을 때 안전 예외). 문서 갱신: DATA_PLACES·OPERATIONS·CLAUDE·ROADMAP.
  - 검증: compileall·verify_frontend PASS. (pytest는 사용자 환경 `uv run -m pytest -q`)
## v1.153 (2026-06-28)
- **문서 인수인계 수준 전면 갱신(코드 변경 없음)** — v1.135~v1.152의 기능이 CHANGELOG에만 있고 구조 문서가 v1.111~v1.125에 멈춰 있던 격차 해소.
  - **CLAUDE.md**: 데이터 모델(Landmark/Place/Consent·UserPref.my_home)·레포 구조(신규 서비스/소스/스크립트)·마이그레이션 head 0018·현재상태 8.1(청주 특화·우리집·UI)·8.2(데이터 적재 상태표)·함정(스코프 크래시·오프라인검증 한계·btn-primary) 반영.
  - **ROADMAP.md**: 최상단에 현재상태 스냅샷(v1.152)+다음 우선순위+기술부채, 완료 로그에 v1.135~152.
  - **README.md**: 청주 특화 3축·우리집·마이페이지·관심단지 시세·전체화면 지도.
  - **OPERATIONS.md**: 청주 특화 데이터 적재 절(seed_landmarks/seed_commute/collect_places + 활성화 표).
  - **TESTING.md**: 오프라인 검증 한계 + 브라우저 스모크 체크리스트(게시판·지도·단지상세·우리집).
  - **DATA.md**: landmarks/places/commute·user_prefs.my_home 테이블.
  - **LANDMARKS.md**: 실제 시드 완료·표시 3곳 현행화. **skills/frontend.md**: 버튼클래스·스코프안전·데이터대기·전체화면지도·우리집동기화 컨벤션.
## v1.152 (2026-06-28)
- **버튼 일관성 정리 + 다크모드 버그 수정** — 주요 액션 버튼(글쓰기·매물등록·로그인·등록·공유하기 등 10곳)을 공통 `.btn-primary` 클래스로 통일. 제각각이던 초록색값·모서리 반경(9/10/11/12)을 하나로, 눌림 피드백(active) 추가.
  - 공유하기 버튼이 하드코딩 `#0F766E`라 **다크모드에서 색이 안 바뀌던 버그** 수정(→ var(--teal) 기반). (카카오·네이버 로그인은 브랜드색 유지)
- **지도 전체화면 레이아웃 수정** — '이 지역 요약' 바가 하단 네비와 어긋나던 문제 보정(bottom 위치·지도 높이 calc를 헤더48+네비60 기준으로 재계산). 지도가 헤더 아래~네비 위 영역을 정확히 채우도록.
  - 검증: verify_frontend PASS.
## v1.151 (2026-06-28)
- **청주 특화: 직주근접 — '🏭 직장·거점 거리'** (단지 상세). 청주 실수요의 핵심인 SK하이닉스·오창·오송 근로자를 위해, 단지에서 청주 주요 거점까지의 **직선거리(km)** 를 표시.
  - 통근권 목적지(CommuteDestination)를 재사용해 좌표 일관성 유지 → `commute.hub_access()` 신설, detail 응답에 `work_access` 추가.
  - **시드에 SK하이닉스 청주캠퍼스 추가**(청주 최대 고용주 — 기존 목록에 누락돼 있었음. 좌표는 근사값, --geocode로 승격 가능).
  - 표시: 직장·산단(전부) / 교통·공공·교육(카테고리별 가까운 3곳). "직선거리이며 통근시간과 다를 수 있음" 명시 + 통근권 도구로 안내. 거점 미시드 시 숨김(왜곡 없음).
  - 적용 조건: 서버에서 `python -m scripts.seed_commute` 1회 실행(통근 도구와 공유).
  - 검증: compileall·verify_frontend PASS, 거리 상식 체크(복대동→SK하이닉스 4.0km ✓). pytest는 사용자 환경에서 `uv run -m pytest -q` 확인 요망.
## v1.150 (2026-06-28)
- **우리집 로그인 서버 동기화** — 우리집을 사용자 설정(prefs.data.my_home)에 저장. 로드 시 서버값 반영, 변경 시 서버 저장. 로그인하면 기기 병합(device→account)으로 다른 기기에서도 우리집 유지. (비로그인은 로컬만)
- **관심 단지 시세 변동 표시** — 관심 단지 목록에 **최근 매매가(억) + 전월 대비%**를 표시.
  - 백엔드: `POST /complex/quotes` — 여러 단지의 최근가·전월대비를 **한 쿼리로 배치 계산**(N개 HTTP 대신 1회). `stats.complex_quotes`.
  - 프런트: FavList가 관심 단지를 배치 조회해 각 행에 시세·Delta 표시. 데이터 없으면 생략(왜곡 없음).
  - 검증: compileall·verify_frontend PASS.
## v1.149 (2026-06-28)
- **우리집 카드에 시세·변동 표시** — 등록된 우리집 단지의 `/complex/detail`을 조회해 홈 우리집 카드에 **최근 매매가(억) + 변동%**를 바로 노출.
  - 변동%: timeseries 마지막 2개월로 '전월 대비' 계산, 없으면 '지역 평균 대비'(vs_region)로 폴백. 실거래 없으면 문구로 안내(왜곡 없음). 로딩 상태 표시.
  - 검증: verify_frontend PASS.
## v1.148 (2026-06-28)
- **우리집 등록 + 마이페이지(더보기 개편)** — 실수요자가 '내 집 중심'으로 앱을 쓰도록.
  - **우리집 등록**: 검색으로 내 아파트 선택 → 로컬 저장(safeStore, 로그인 불필요). 홈 최상단 'MyHomeCard'에 우리집 표시(없으면 등록 버튼) → 탭하면 우리집 시세(단지 상세)로.
  - **더보기 → 마이페이지**: 프로필 헤더(이름/역할/로그인) + 우리집(등록·변경·삭제·시세보기) + 바로가기(관심/청약/게시판) + 기존 집찾기 도구(통근·예산·대출).
  - 검색 오버레이를 '우리집 등록' 모드로 재사용(homePick). 데이터/서버 없이 동작, 추후 서버 동기화 가능한 구조.
  - 검증: verify_frontend PASS(헬퍼 전역 스코프 확인).
## v1.147 (2026-06-28)
- **지도 전체화면 활용** — 네이버 지도처럼 지도가 화면을 꽉 채우도록 개편.
  - 지도 높이를 `calc(100dvh - 122px)`로 키우고 가장자리까지(좌우 여백 제거) 확장.
  - 거래유형·유형·주변시설·호재 필터를 지도 위 **상단 오버레이**(가로 스크롤 칩)로, '이 지역 요약'은 **하단 오버레이 바**로 이동해 세로 공간을 지도에 양보.
  - 지도 탭에선 상단 배너·갱신줄·하단 면책 footer를 숨겨(다른 탭은 그대로) 지도 영역 최대화.
  - 검증: verify_frontend PASS.
## v1.146 (2026-06-28)
- **호재를 지도에 핀으로** — 지도 탭에 '🏗 개발 호재' 토글 추가. 켜면 좌표 있는 호재(SK하이닉스 P&T7·방사광가속기·테크노폴리스·OSCO 등)를 상태색 핀으로 표시(줌 무관). 핀 클릭 시 요약·출처 InfoWindow. 가격/시설 마커와 독립 레이어. (호재는 seed_landmarks 실행 후 표시)
- **초품아 뱃지** — 단지 상세 헤더에 초등학교 도보권이면 배지. 초등학교 ≤400m = '🏫 초품아', ≤700m = '🏫 초등 도보권' + 학교명·거리. 백엔드 school_access(초등 최단거리) 재사용 → POI(학교) 데이터 있으면 표시, 없으면 숨김(왜곡 없음).
  - 검증: verify_frontend PASS.
## v1.145 (2026-06-28)
- **청주 특화 콘텐츠 2종 추가** (실수요자·육아 부모 타겟).
  - **A. 홈 '🏗 청주는 지금' 개발 이슈 카드(CityIssues)** — /landmarks(호재) 조회해 상태·요약·예상연도·출처와 함께 표출. 데이터 없으면 숨김(왜곡 없음). 투자 판단 아님 고지 포함.
    - **실제 호재 시드**(scripts/seed_landmarks.py, 출처 확인): SK하이닉스 P&T7(청주테크노폴리스, 19조·2028), 오창 방사광가속기(2028경 가동), 청주테크노폴리스 산단, 북청주역세권(예정), 청주 OSCO(2025 개관). 좌표는 개략 위치, summary는 사실만.
  - **B. 단지 상세 '🧸 육아 환경' 카드(KidsEnv)** — 반경 내 어린이집·유치원/학원/소아과·병원/도서관/체육/약국 개수 요약. d.places(공공데이터) 사용 → 시설 데이터 적재 시 자동 작동, 없으면 숨김.
  - 적용: `python -m scripts.seed_landmarks` 실행 시 호재 노출. 육아 카드는 시설 데이터 적재 필요.
  - 검증: compileall·verify_frontend PASS.
## v1.144 (2026-06-28)
- **지도 주변시설(POI) 표출 구조** — 데이터만 적재되면 자동 작동하도록 골격 완성(현재 시설 데이터 없으면 아무것도 안 뜸, 왜곡 없음).
  - 백엔드: `/places/map?min_lat&max_lat&min_lng&max_lng&categories=` 엔드포인트 + `places.in_bounds()` — 지도 영역(bbox) 내 시설 마커(education/sports/living 필터).
  - 프런트: 지도 탭에 **주변시설 토글**(🎓 학원 / 🏃 체육 / 🏪 생활). 선택 + **확대(zoom≥15)** 시 현재 화면 범위의 시설을 흰 말풍선 마커로 표출. 카테고리별 색(학원 보라·체육 파랑·생활 청록). idle마다 현재 bbox로 재조회, 상한 200개.
  - 가격 마커와 독립된 레이어(별도 ref)라 기존 시세 마커에 영향 없음.
  - ⏭ 남은 것: 시설 데이터 적재(scripts.collect_places + NEIS/공공데이터 키). 적재되면 토글만으로 바로 보임.
  - 검증: compileall·verify_frontend PASS.
## v1.143 (2026-06-28)
- **단지 상세 개편**.
  - **면적 병합**: 근소한 전용면적 차이(예: 23.1평·23.2평 = 76.3㎡·76.7㎡)를 **같은 평형으로 병합**(round(평) 기준, 대표 전용면적=그룹 중앙값). 다른 앱처럼 평형 단위로 정리. (stats.py 그룹핑 키 변경)
  - **섹션 재배치**: 거래활발(VolumeSignal)·위치(지도)·인근 인프라를 **상단(최근 매매가 바로 밑)으로** 이동.
  - **학군 섹션 삭제**(인근 인프라와 중복).
  - **면적별 상세**: 기본 **접힘** + **평(면적) 오름차순 정렬**(선택 평형이 있으면 펼친 상태로).
  - 검증: compileall·verify_frontend PASS.
- (예정) 지도 확대 시 학원·체육시설 등 생활 인프라 마커 표출 — 별도 작업(장소 데이터 적재 필요).
## v1.142 (2026-06-28)
- **게시판·매물 다크모드 수정 + 버튼 톤 정리**.
  - 다크모드 안 먹던 하드코딩 밝은색을 변수/틴트로: 댓글 카드 배경(#fff/#F6FAFA→var(--surface-solid)/(--surface-2)), 중개업자·개인 뱃지(#E7EEF6/#EEF1F1→틴트/var(--chip)), 이미지 플레이스홀더(#EEF1F1→var(--surface-2)), 취소·더보기 테두리(#d3dada→var(--line)), 댓글 취소 배경(#e7efef→var(--surface-2)).
  - **좋아요·스크랩 버튼**을 영역 나누는 테두리 알약 → **토스식**(테두리 없음, 서피스 배경, 눌리면 은은한 틴트+색). 게시판·매물 공통 원칙 적용.
  - 주요 CTA(글쓰기·매물 등록·전화 문의)는 강조 유지.
  - (공유용 이미지 카드의 흰 배경은 의도된 것이라 유지.)
  - 검증: 괄호 균형·verify_frontend PASS.
## v1.141 (2026-06-28)
- **지도 마커 라벨 → 총액(억) 표기** — 매매는 평단가 대신 **매매가 중앙값(총액)을 억 단위**로(예: 5.2억), 전세/월세는 보증금 억. 클러스터도 총액 중앙값으로. 색(가격 히트맵)은 평단가 기준 유지. (백엔드 median_amount 활용)
- **거래 급상승·대장 아파트 티커 = 상위 5개만 회전** — 펼치기 전 자동 회전 배너는 top 5만 순환, 클릭해 열면 RankSheet에서 **전체(최대 50) 그대로**.
  - 검증: 괄호 균형·verify_frontend PASS.
## v1.140 (2026-06-28)
- **지도 마커 개선(부동산앱 스타일)** — 기존 꼬리 없는 단순 알약 → **말풍선 꼬리(포인터)로 위치를 정확히 가리키는 가격 버블** + 더 또렷한 드롭섀도. 네이버부동산·호갱노노류 룩.
  - 클러스터(여러 단지): 어두운 알약 → **원형 배지**(개수 + 중앙값), 흰 테두리·그림자.
  - 가격 히트맵 색(파랑 저가→빨강 고가)은 정보성이라 유지. 단일 마커는 가격대 색 버블+흰 테두리.
  - 검증: 괄호 균형·verify_frontend PASS.
## v1.139 (2026-06-28)
- **버튼 톤 정리(토스식 — 선택만 은은하게, 초록 채움 제거)** — 참고 이미지처럼 필터·토글이 튀지 않고 배경 톤을 따르도록.
  - 지도 필터 `chip()`: 선택 시 초록(TEAL) 채움 → **서피스 톤 + 옅은 그림자 + 잉크색 텍스트**, 미선택은 투명+뮤트.
  - 필터 토글 `.tog`: 경계선 제거, 선택 `.tog.on`을 teal 채움 → 서피스+잉크+그림자.
  - 세그먼트(게시판/매물·분양/청약): 선택 텍스트 TEAL → **잉크색**으로 통일(중립).
  - **헤더 알림·메뉴 버튼 경계 제거** → 배경에 녹아들게(투명 배경, 테두리 없음).
  - 주요 액션 버튼(글쓰기·한도 계산 등 primary CTA)은 강조 유지(변경 없음).
  - 검증: 괄호 균형·verify_frontend PASS.
## v1.138 (2026-06-28)
- **진입 속도 개선(로딩 느림 대응)** — 홈 대시보드(board)가 부르는 집계 9종 중 유일하게 캐시가 없던 `landmark_apts`에 `@stat_cached` 추가(게다가 v1.131에서 5→50개로 키워 매 진입마다 재계산되던 지점).
  - 캐시 TTL 백스톱 600→3600초. 데이터 버전 무효화가 1차라 안전하며, 저트래픽에서 10분마다 재계산되던 것을 방지.
  - **시작 시 캐시 워밍업** — 서버 startup에서 홈 집계(city/trend/ranking/trending50/landmark50/movers 등)를 백그라운드 스레드로 미리 계산. 첫 사용자가 콜드 캐시 재계산을 기다리지 않도록. 실패해도 서비스 무영향.
  - 검증: compileall PASS.
## v1.137 (2026-06-28)
- **게시판 크래시 수정(중요)** — v1.136에서 게시판/매물 토글에 쓴 `segBtn`이 다른 컴포넌트의 지역 함수라 스코프 밖 `ReferenceError`로 게시판 진입 시 크래시. 인라인 스타일로 교체해 해결. (오프라인 괄호검사·컴파일은 런타임 ReferenceError를 못 잡으므로 향후 주의.)
- **홈 첫 화면 '청주 아파트 시세' 히어로 숨김** — 검색으로 시세 열람 가능하므로 홈 상단 요약 카드 제외(`{false&&...}` 가드, 코드 보존·부활 가능).
- **청약 탭 내부 분양/청약 세그먼트** — [🏢 분양 정보] / [📋 청약 일정] 로 분리(가독성). 분양=전체 공고+상태필터(전체/접수중/접수예정/마감), 청약=접수중·예정만 임박한 순 정렬(지금 넣을 수 있는 청약). 같은 데이터, 관점만 분리(왜곡 없음).
  - 검증: 괄호 균형·verify_frontend PASS.
## v1.136 (2026-06-28)
- **매물 → 게시판 안으로 통합** — 게시판 진입 시 상단 세그먼트 토글 **[💬 게시판] / [🏠 매물]** 로 나눠서 보기. 매물 선택 시 기존 `ListingsTab`을 그대로 렌더(글쓰기·상세·필터 유지).
  - 하단 탭에서 '매물' 제거 → 홈·지도·청약·게시판·더보기 = **5탭**.
  - 섹션 상태는 App(`boardSection`)이 관리. 매물 딥링크(검색의 매물 클릭·중개사 대시보드 '매물 보기/열기')는 `setTab("listing")` → **게시판 탭 + 매물 섹션**으로 우회(안 깨지게). 매물 상세 openId도 전달.
  - `ListingsTab` 컴포넌트는 그대로 재사용(중복 구현 없음).
  - 검증: 괄호 균형·verify_frontend PASS.
## v1.135 (2026-06-28)
- **시세 기능 숨김(삭제 아님, 부활 가능)** — 상단 검색으로 단지 진입 시 시세(가격·추이·평형별·동네대비)가 이미 다 보여 기능이 겹치므로 시세 전용 탭을 숨김.
  - 하단 탭에서 '시세' 제거(홈·지도·청약·매물·게시판·더보기 = 6탭).
  - 홈 '청주 전체 시세 보기 →' 버튼 숨김(`{false&&...}` 가드 — 코드 보존).
  - 지역(구) 클릭(`goGu`)을 시세 탭 → **지도 탭**으로 우회(진입점 안 깨지게). `priceGu`/`priceView` 상태와 `PriceHub` 컴포넌트, `tab==="price"` 렌더 분기는 **그대로 보존**.
  - ⏪ 부활 방법: NAV에 `["price","시세"]` 재추가 + 홈 버튼 `{false&&` 제거 + `goGu`의 `setTab("map")`→`setTab("price")`. (핸드오버 참고)
  - 검증: 괄호 균형·verify_frontend PASS.
## v1.134 (2026-06-28)
- **'더보기' 탭 신설 + 집찾기 도구 이동** — 홈에 있던 큰 카드 3종(통근권으로 집 찾기·내 예산 맞춤 추천·내 대출 한도 계산)을 홈에서 빼고 새 **더보기 탭**(하단 7번째 탭)으로 이동. `MoreTab` 컴포넌트 + Icon "more"(3줄) 추가.
  - 첫 진입 '환영 + 이렇게도 찾을 수 있어요'(🚆통근/💰예산/🏦대출 칩) 추천 카드는 **홈에 그대로 유지** — 발견 동선은 남기고, 전체 도구는 더보기에.
  - 하단 탭: 홈·지도·시세·청약·매물·게시판·**더보기**(7탭).
  - 검증: 괄호 균형·verify_frontend PASS.
## v1.133 (2026-06-28)
- **로딩 화면 트렌드 정비(2026 스켈레톤 UX)** — 웹 검색으로 최신 로딩 UX 트렌드 확인 후 반영(콘텐츠 로딩=스켈레톤, 스피너 최소화, 레이아웃 미러링, reduced-motion 존중).
  - shimmer 애니메이션 개선(ease-in-out 1.25s, 하이라이트 대비↑), **prefers-reduced-motion 시 shimmer 대신 은은한 펄스**(접근성).
  - **레이아웃 맞춤 스켈레톤** 신규: `SkeletonRow`(썸네일+2줄+값), `SkeletonList`(카드 내 divider 행), `SkeletonStat`(요약 통계 카드). 실제 화면 구조를 미리 보여줘 체감 속도↑.
  - 홈 로딩을 통계+목록 스켈레톤으로, 시세 목록 로딩에도 스켈레톤 적용(기존 텍스트만 → 구조 표시).
  - 검증: 괄호 균형·verify_frontend PASS.
## v1.132 (2026-06-28)
- **시세 출처·계산 표기 보강** — 시세 요약 지표(평균 매매 중앙값·전세가율)에 Info 툴팁(계산식+자료 출처: 국토교통부), 하단 설명에 출처·평단가/전세가율 계산식 명시.
- **첫 진입 스플래시 화면** — 앱 로드 시 청록 배경 + 집 아이콘 + '청집사 / 청주 부동산, 한눈에' 1.5초 표시 후 페이드아웃(탭하면 즉시 넘김).
- **최근 본 단지 → 거래급상승 위로** 이동(홈 상단 노출).
- **분양 정보 보강** — 청약 탭을 '청주 분양·청약'으로 명확화(분양 공고+청약 정보 안내), 상세에 **시행사·모집공고일** 추가(applyhome BSNS_MBY_NM 등), 목록 6→10개씩.
  - 검증: 괄호 균형·verify_frontend·compileall PASS.
## v1.131 (2026-06-28)
- **시트 아래로 쓸어 닫기 일괄 수정** — 공통 `Sheet` 컴포넌트에 스와이프-투-클로즈(맨 위에서 아래로 드래그 시 닫힘) 추가. 그동안 `SheetShell`(아파트 상세·매물·게시글)만 됐고 `Sheet` 기반은 안 됐던 것을 해결 → **거래급상승·대장아파트·단지 빠른보기·청약 상세 등 전부** 이제 아래로 쓸면 닫힘.
- **거래 급상승·대장 아파트 10개+더보기** — RankSheet를 `MoreList`로: 처음 10개 → '더보기' 10개씩 → **최대 50개**. 백엔드도 확대: 거래급상승(trending) 8→50, 대장아파트(landmark) 5→50.
  - 검증: 괄호 균형·verify_frontend·compileall PASS.
## v1.130 (2026-06-28)
- **브랜드 '청집사' 전환 + 상단/하단 UI 개편 + 앱 아이콘**.
  - 타이틀 **청주시세 → 청집사** 전면(상단바·매니페스트·앱 제목·환영문구·capacitor appName).
  - **상단바 자연스럽게**: 청록 그라데이션 바 제거 → 기본 배경과 블렌드(잉크 텍스트), 검색/알림/메뉴 버튼은 서피스톤+헤어라인.
  - **상단 우측 메뉴 외부클릭 닫힘**: ☰ 메뉴가 바깥 클릭 시 사라지도록 backdrop 추가.
  - **하단 메뉴바 확대**: 높이 48→60, 아이콘 24, 폰트 12, 패딩↑.
  - **탭 순서**: 홈 다음에 **지도**(홈·지도·시세·청약·매물·게시판).
  - **앱 아이콘 신규**: 청록 그라데이션 라운드스퀘어 + 흰 집(지붕·문·창) 심볼. 192/512/maskable/apple-touch 4종 재생성.
  - 검증: 괄호 균형·verify_frontend PASS.
## v1.129 (2026-06-28)
- **게시판 '이번 주 베스트' 접기 기능** — 항상 펼쳐진 목록 → `Collapsible`로 감싸 **작게 시작(기본 접힘) + 탭하면 펼침**(개수 뱃지 표시). 홈 거래급상승처럼 공간 절약.
- **지도 필터 한 줄 배치** — 거래유형(매매/전세/월세)·매물종류(아파트/오피스텔…)가 두 줄로 분리돼 있던 것을 **한 줄**로 합침(가운데 구분선, 좁으면 자동 줄바꿈).
- **시세 더보기 10개씩** — 단지 상세 '최근 실거래'(5→10)와 시세 그룹 목록(4→10) 초기 표시를 10개로, 더보기 증분 10개 유지.
  - 검증: 괄호 균형·verify_frontend PASS.
## v1.128 (2026-06-28)
- **구글플레이 출시 준비(Capacitor · Android)**.
  - `frontend/capacitor.config.json`: appId를 예시값 → **com.cheongzipsa.app** 확정, appName "청주시세".
  - `store/GOOGLE_PLAY_RUNBOOK.md` 신규: 실전 순서서(웹빌드 시 VITE_API_BASE 주입 필수 · cap add/sync · 아이콘 · 키스토어 서명 · Play Console 등록 · 내부테스트→프로덕션 · CORS/소셜로그인 주의점).
  - ⚠️ 네이티브 빌드·서명·업로드는 운영자 PC(Android Studio·구글플레이 계정 $25)에서 수행. 샌드박스 불가. iOS는 Mac+Xcode 필요로 후순위.
  - 코드 변경 없음(설정·문서). 백엔드/프런트 무영향.
## v1.127 (2026-06-28)
- **단지 상세 심화 — "동네 대비 포지셔닝"**(축1: 지금 데이터로 더 깊게). 추가 키·데이터 불필요, **기존 실거래로 즉시 작동**.
  - `complex_detail`에 `vs_region` 추가: 단지 평단가(만원/평) 중앙값 vs **같은 구 평균 평단가** → "흥덕구 평균 대비 +12%"처럼 하이퍼로컬 비교(평단가 기준으로 평형 구성 차이 보정). 표본수 포함, 데이터 없으면 None(왜곡 없음).
  - 프런트: 단지 빠른보기 + 전체 상세 헤더에 "📍 OO구 평균 대비 ±N%"(한국식 색: +빨강/−파랑) + 평단가 비교 노출.
  - 호갱노노식 절대값 나열이 아니라 **"이 단지가 동네에서 비싼가/싼가"**를 한눈에 — 전국 앱이 약한 하이퍼로컬.
  - 테스트 `test_stats_lowmem`(+1): 비싼 단지가 구 평균 대비 +%. (총 136→137)
  - 검증: compileall·verify_frontend·괄호 균형 PASS.
## v1.126 (2026-06-28)
- **청약 화면 정보 강화 — '보고 싶게'**. 청약 카드를 정보 나열 → **비주얼 배너 + D-day**로.
  - `SubCard`: 상태별 색 그라데이션 배너(단지명·위치·세대수) + **D-day 뱃지**(접수 D-n/마감 D-n, 임박 시 강조) + 분양가·경쟁률·가점 칩 + 주택형 미리보기(3개+"자세히").
  - `SubDetail`: **📍지도** 버튼(네이버 지도 위치 검색) + 청약홈 버튼 나란히.
  - 백엔드 `applyhome`: 아이템에 `begin/end` 추가(D-day 계산용).
  - ⚠️ 분양 사진은 공공 API에 없음 → 가짜 사진 대신 위치·정보 기반 비주얼(왜곡 없음). 향후 공고 썸네일/지도 이미지 연동 여지.
  - 검증: 괄호 균형·verify_frontend·py_compile PASS.
## v1.125 (2026-06-28)
- **청주 개발 호재 지도(Landmark) — 구조 구축**(데이터는 나중에, 차별화: 청주 하이퍼로컬).
  - 모델 `Landmark` + 마이그레이션 0018: 위치+사실+출처. **왜곡 방지** 내장 — status(확정/추진/계획)·source 필수, summary는 사실만.
  - 서비스/API: `/landmarks`(지도용 전체)·`/landmarks/near`(단지 주변 4km 거리순)·`/landmarks/labels`. 단지 상세 응답에 landmarks 연결.
  - 프런트: 단지 상세에 "주변 개발 호재" 섹션(단계 뱃지·연도·거리·출처 링크 + "집값 변동 보장 안 함·투자 본인 책임" 고지).
  - 시드: `scripts/seed_landmarks.py`(빈 리스트 + 작성 가이드 → 나중에 출처·좌표와 채우면 upsert). 문서 `LANDMARKS.md`.
  - 테스트 `tests/test_landmarks.py`(3): 주변 거리·비활성 제외·좌표없음. (총 133→136)
  - ⏳ 지도 탭 핀: 백엔드 준비 완료, 프런트 핀은 데이터+화면 확인 후 안전 연결(블라인드로 작동 지도 깨뜨릴 위험 회피).
  - 검증: compileall·verify_frontend·괄호 균형 PASS.
## v1.124 (2026-06-28)
- **가족 맞춤 동네 점수 엔진(차별화 핵심)** — 사용자가 중요시하는 생활 항목(학원·운동·어린이집·도서관·병원·공원)에 중요도(0~5)를 주면, 단지 주변 '실제' 공공데이터 시설로 동네를 점수화.
  - `app/services/places.fit_score()`: 항목별 subscore = 근접도 60% + 밀집도 40%, overall = 가중평균. **데이터 없는 항목은 점수를 지어내지 않고 '데이터 없음'으로 제외(왜곡 없음).** 좌표 없으면 None.
  - API `GET /places/fit-score`(가중치 쿼리) + `/places/fit-categories`(항목 목록).
  - 호갱노노식 '학원 N개' 나열이 아니라 **"우리 가족 기준 이 동네가 맞는가"**를 점수로 — 전국 앱이 못 하는 하이퍼로컬·개인화.
  - 테스트 `tests/test_places.py`(+2): 가중치 반영·데이터없음 None·좌표없음. (총 131→133)
  - 검증: compileall·verify_frontend PASS.
  - ⚠️ 실제 점수는 Place 데이터 적재 후 의미. 지금은 데이터 없으면 '데이터 없음'. 개인화 입력 UI는 다음 단계(데이터+화면 확인과 함께).
## v1.123 (2026-06-28)
- **코드 정리(죽은 코드 제거)** — 전체 모듈 import 참조·라우터 등록·미사용 import를 기계적으로 스캔.
  - 삭제: `app/data/sample_listings.py`(SAMPLE_LISTINGS)·`app/data/sample_posts.py`(SAMPLE_POSTS/COMMENTS) — 외부 참조 0건 교차검증 후 제거(실사용 시드는 sample_feed·sample_transactions). 백엔드 80개 파일·약 9,380줄.
  - 확인만 하고 유지: 라우터 24개 전부 정상 등록(죽은 라우터 없음). `session.py`의 `from app import models`는 미사용처럼 보이나 **모델 등록 부수효과 import**(noqa F401)라 유지 필수. 내 매물·내 댓글 등 관리 화면 카드도 유지.
  - 검증: compileall·verify_frontend PASS, 테스트 131 유지. (삭제 파일 백업: /tmp)
## v1.122 (2026-06-28)
- **UI 정리 2차** — 알림 목록을 카드 나열 → 구분선 행(한 박스, 안 읽음 표시 유지). 구분선 색을 전부 `var(--line)`로 통일(.listrow·.txrow·table·.rankno) → 라이트/다크 일관 + 옛 하드코딩 색 제거.
  - 내 매물·내 댓글 등 관리 화면은 액션 버튼이 얽혀 있어 카드 유지(블라인드 변경 위험 회피).
  - 검증: 괄호 균형·verify_frontend PASS.
## v1.121 (2026-06-28)
- **🔧 데이터 출처 정정 — 학원 API를 실제 제공처(NEIS)로 수정**. "진짜 API 활용 가능한 데이터만" 원칙 반영.
  - 확인 결과: data.go.kr '전국학원및교습소표준데이터'(15096277)는 **CSV 파일** 제공이고 실제 Open API는 **NEIS(open.neis.go.kr) `acaInsTiInfo`** 제공. 기존 odcloud 추정 URL은 오류 → NEIS API로 재작성(`app/sources/academy.py`, source_dataset=neis_academy).
    - 시도교육청코드(충북 M10)로 요청 후 청주 필터. 전국 확장은 OFFICE_CODES 추가만으로. NEIS는 좌표 미제공 → scripts.geocode로 보강. ⚠️ NEIS 키는 data.go.kr 키와 별도(ACADEMY_SERVICE_KEY=NEIS 키).
  - 어린이집(15013108)은 data.go.kr odcloud OpenAPI 실재 확인(uddi)·좌표/놀이터수/CCTV/정원·현원 포함.
  - `DATA_PLACES.md`에 **API 검증 상태표** 추가: 학원·어린이집=확인, 체육·도서관·의료·유치원·도시공원(놀이터)·실외운동기구=데이터셋 실재하나 엔드포인트는 활용신청 후 확정(코드 URL은 추정 placeholder로 명시).
  - 테스트: test_academy를 NEIS 필드(ACA_NM 등)·좌표 None 기준으로 갱신(4). 총 131 유지.
  - 검증: compileall·verify_frontend PASS.
## v1.120 (2026-06-28)
- **게시판 '이번 주 베스트' 컴팩트화** — 큰 글 카드 3개 나열 → 홈 '거래 급상승'과 동일한 **순위 목록**(🥇🥈🥉/번호 + 제목 + 동네·단지 + ♥ 좋아요)으로 한 박스에 정리. 화면 차지 줄고 일반 글 목록과 시각적으로 구분됨.
  - 검증: 괄호 균형·verify_frontend PASS.
## v1.119 (2026-06-28)
- **메모리 최적화 일관성 — places.nearby 경량화**. 단지 상세 조회마다 호출되는 주변시설 조회가 전체 Place ORM 객체를 적재하던 것을 **필요한 7개 컬럼만**(subcategory·name·lat·lng·course·tuition·source) 경량 Row 조회로 전환. bbox 선필터(반경 1.2km)와 함께 메모리·속도 개선. stats.py 집계 최적화(v1.111)와 동일 원칙으로 통일.
  - 검증: compileall PASS. 출력 동일(테스트 영향 없음).
## v1.118 (2026-06-28)
- **리스트 UI 정리 — 카드 줄줄이 → 구분선 행**(직방 '이야기' 류). 테스터 선호 반영.
  - `.feedrow` 유틸 추가(헤어라인 구분선 + 탭 피드백). `PostCard`(게시판 글)·`ListingCard`(매물)를 개별 카드 박스에서 **구분선 행**으로 전환 → 목록이 깔끔하게 연속. 매물 썸네일은 자체 라운딩 부여.
  - 검증: 괄호 균형·verify_frontend PASS. (UI는 머신 빌드로 최종 확인)
## v1.117 (2026-06-28)
- **🐞 긴급 버그픽스 — stats.py NameError(get_settings)**. 대시보드/시세 집계 호출 시 `NameError: name 'get_settings' is not defined`로 전부 실패하던 문제.
  - 원인(v1.111 회귀): `_load`(stats.py 90행)가 `get_settings().aggregate_months`를 쓰는데, import가 `_cutoff_date` **함수 내부 지역 import**에만 있어 다른 함수에선 미해결.
  - 수정: `from app.core.config import get_settings`를 **모듈 상단**으로 이동(20행). 중복 지역 import 제거.
  - 영향: top_trades·city_summary·by_region 등 `_load` 사용 집계 전부 정상화.
  - 검증: compileall PASS. 머신에서 `uv run -m pytest -q`(test_stats/test_stats_lowmem) 통과로 최종 확인 권장 — 이 버그는 그 테스트가 잡는 종류.
## v1.116 (2026-06-28)
- **UI/UX 현대화(토큰 기반, 앱 전체)** — 테스터 피드백("올드하다·안 세련됨") 반영.
  - 글래스모피즘(반투명+블러) + 3색 파스텔 그라데이션 배경(2021~22 트렌드) → **깨끗한 단색 배경 + 솔리드 흰 카드 + 또렷한 헤어라인 경계 + 미니멀 그림자**(토스·당근 류 2026 감성).
  - `frontend/index.html` 디자인 토큰만 교체(컴포넌트 무수정 → 저위험·앱 전체 일괄 적용): 배경 플랫(var(--bg1)), `--surface`/카드 솔리드, 경계 다크 헤어라인, 카드 radius 16→18, 그림자 경량화. 하단 탭바(.nav)도 글래스→솔리드 헤어라인. 다크모드도 플랫 재정의.
  - Pretendard·한국식 상승=빨강/하락=파랑 유지. ⚠️ 렌더는 사용자 머신 확인 필요(롤백 쉬움: 토큰만 되돌리면 됨).
- **도서관·어린이집 수집기 추가**(생활 인프라 확장 마무리).
  - `app/sources/library.py`(도서관, WGS84 좌표·좌석수·운영시간) + `app/sources/daycare.py`(어린이집·유치원, 정원·현원). 공통 `places_common` 사용.
  - `scripts/collect_places.py`: `library`·`daycare` 추가 + `all`에 포함(학원·체육·의료·도서관·어린이집 5종).
  - 테스트 `tests/test_library_daycare.py`(4). (총 127→131)
  - 검증: compileall·verify_frontend·style 균형 PASS. ⚠️ URL·필드는 Swagger 확정(tolerant 흡수).
## v1.115 (2026-06-28)
- **체육·의료 수집기 추가**(학원에 이어 생활 인프라 확장).
  - 공통 유틸 `app/sources/places_common.py`: tolerant 필드픽·좌표·청주 필터·페이지 수집 + **EPSG:5174→WGS84 변환**(pyproj, 한국 범위 sanity, 실패 시 좌표 None — 틀린 좌표 저장 금지).
  - `app/sources/sports.py`: 체육시설(체육관·수영장·풋살 등). WGS84 좌표·**사용료(tuition)**·유형(course)·수용인원. subcategory="sports".
  - `app/sources/medical.py`: 의료기관. **WGS84 필드 우선 → 없으면 TM5174 변환**. 종별→subcategory(병원/의원=hospital, 약국=pharmacy).
  - `scripts/collect_places.py`: `sports`·`medical`·`all` 명령 추가(upsert·중복방지).
  - requirements: `pyproj`(선택, 의료 좌표 변환). config 키는 academy/molit 재사용.
  - 테스트 `tests/test_sports.py`(3)+`tests/test_medical.py`(4): 정규화·분류·청주필터·좌표없음 None·종별(약국). 네트워크/pyproj 불필요. (총 120→127)
  - 검증: compileall PASS. ⚠️ 각 데이터셋 URL·필드는 활용신청 후 Swagger로 확정(tolerant라 대부분 흡수). 실수집은 머신/서버.
  - 문서: DATA_PLACES(수집 명령)·ROADMAP.
## v1.114 (2026-06-28)
- **학원·교습소 수집기(차별화 첫 실데이터)** — 전국학원및교습소표준데이터(공공데이터) → Place 적재.
  - `app/sources/academy.py`: applyhome 패턴의 **tolerant 필드 매핑**(학원명/acaNm 등 여러 후보 자동 흡수) → Swagger 없이도 흔한 응답 흡수. 청주(충북) 필터 + 구→법정동코드 매핑 + 분야/과정 텍스트 → 세분류(`classify_academy`). 키 없으면 0건(안전).
  - `scripts/collect_places.py academy`: 정규화→Place upsert(source_key 중복방지). 좌표 없는 행은 geocode로 보강.
  - config `academy_service_key`(없으면 MOLIT 키 재사용) + .env.example.
  - 테스트 `tests/test_academy.py`(4): 다른 필드명 흡수·세분류(외국어/체육)·청주외 제외·이름없음 제외. 네트워크 불필요(정규화 로직만). (총 116→120)
  - 검증: compileall PASS. ⚠️ `ACADEMY_URL`·필드는 활용신청 후 Swagger로 실제값 확정 필요(tolerant라 대부분 흡수). 실수집은 머신/서버에서.
  - 문서: DATA_PLACES(수집 실행)·ROADMAP.
## v1.113 (2026-06-28)
- **생활·교육·운동 인프라 기반(Place) — 차별화 1단계**(공공데이터로 깊고 정확하게 → 성장모델).
  - 통합 모델 `Place`(model) + 마이그레이션 0017 — 학원·체육시설·도서관·병원 등을 **한 모델로 normalize**. `source`(public/claimed/ad)·`claimed_by` 자리를 미리 둬 **향후 업체 직접 등록·홍보를 재작업 없이** 얹도록(부록 B 원칙). 좌표 없으면 거리/지도 제외(왜곡 방지).
  - 서비스 `app/services/places.py`: 학원 분야/과정 텍스트 → 세분류 키워드 분류(`classify_academy`: 입시·외국어·예체능·체육·컴퓨터·기타), 반경 조회(`nearby`, haversine), 지역 요약(`by_region`).
  - API `app/api/places.py`: `/places/near`·`/places/region/{code}`·`/places/labels`. 단지 상세 응답에 `places` 추가(주변 학원·운동·생활).
  - 프런트: 단지 상세에 "주변 학원·운동·생활" 섹션(세분류별 개수·거리·공개 수강료).
  - 문서 `DATA_PLACES.md`: 분야별 **정확한 공공데이터셋 매핑**(학원교습소·체육시설·공공시설개방·도서관·의료기관)·좌표계(⚠️ 의료 EPSG:5174→WGS84)·갱신주기 + 수집기 청사진.
  - 테스트 `tests/test_places.py`(4): 분류·반경 거리필터·좌표없음 None·지역 집계. (총 112→116)
  - 검증: compileall·verify_frontend·괄호 균형 PASS. ⚠️ 데이터 적재는 수집기(다음 단계, 키 발급+Swagger 확정) 후. 지금은 데이터 없으면 빈 섹션(안전·additive).
## v1.112 (2026-06-28)
- **모바일 앱 느낌 — 핀치 줌/바운스 차단**(웹·PWA·네이티브 공통 적용).
  - `frontend/index.html` viewport에 `maximum-scale=1.0, user-scalable=no, viewport-fit=cover` 추가 → 손가락 확대/더블탭 줌 차단(웹사이트가 아닌 앱처럼 고정). 노치 안전영역 대응(viewport-fit).
  - CSS: `overscroll-behavior:none`(당겨서 새로고침·바운스 제거), `-webkit-tap-highlight-color:transparent`(탭 회색 플래시 제거), `text-size-adjust:100%`(글자 자동 확대 방지). 텍스트 선택·스크롤은 유지.
  - ⚠️ 접근성: user-scalable=no는 저시력 사용자의 확대를 막을 수 있고 iOS 일부 버전은 무시함. 앱 느낌 우선의 트레이드오프.
## v1.111 (2026-06-28)
- **메모리(OOM) 근본 수정 — 집계를 DB 레벨 윈도우로**. 배포 후 `/dashboard/summary`·`/overview`가 512MB 초과로 502(OOM)나던 문제 해결.
  - 원인: `_load`(집계 20여 함수가 사용)가 전체 거래를 메모리에 올린 뒤 파이썬에서 12개월만 거름 + `by_region`/`trend`/`gu_price_ranking`/`recent_trades`가 구별로 **전 기간**을 적재.
  - 수정: `_load_window(db, pt, months)` 도입 — `contract_date >= cutoff` 를 **SQL where**로 필터. 모든 집계가 필요한 기간만 조회:
    - `_load` → 최근 12개월(SQL), `city_summary`(전년대비) → 16개월, `by_region`/`gu_price_ranking` → 16개월, `trend` → 표시구간+2, `active_regions` → 8개월, `top_movers`/`recent_trades` → 60개월.
  - 결과: 무제한 전체조회 0개. 데이터가 수년 쌓여도 메모리 일정(윈도우 상한). `_load_all`은 정의만 유지(미사용).
  - ⚠️ 의미 변화(의도적): 구별 평균/평단가가 '전 기간 평균'→'최근 16개월'로. 앱의 윈도우 기반 설계('현재 시세')와 일관, 도시 헤드라인과도 정합. 표시 수치가 소폭 달라질 수 있음.
  - 검증: compileall PASS. ⚠️ pytest 실행/실제 502 해소는 머신·재배포에서 확인(샌드박스는 sqlalchemy 미설치).
## v1.111 (2026-06-28)
- **메모리 최적화 — 집계 OOM 근본 수정**(Render 512MB에서 /dashboard/summary·overview 가 512MB 초과로 OOM 502).
  - 원인: 집계 로더가 거래를 **전체 ORM 엔티티**(행당 ~1KB+ + identity map)로 메모리에 적재.
  - 수정: `_load_window`와 신규 헬퍼 `_rows_where`가 **집계에서 실제 쓰는 16개 컬럼(`_AGG_COLS`)만** 경량 Row로 조회. 소비 코드(25개 집계 함수)는 `r.deal_amount` 식 속성 접근 그대로 → 변경 없음. 컬럼 전수 조사로 누락 없음 확인(r/x/latest/prev 모두 16컬럼 내, c/cx는 Complex 별도).
  - 적용 위치: `_load_window`(전 집계 공통) + `by_region`·`trend`·`gu_price_ranking`·`recent_trades`(구별 윈도우 직접 로드). 단일 단지 쿼리(compare_one 등)는 소량이라 유지.
  - 효과: 집계 시 행당 메모리 대폭 절감 + ORM identity map 미사용 → 512MB에서도 동작 목표.
  - `render.yaml`: `WEB_CONCURRENCY` 2→1(512MB에선 워커 2개가 메모리 2배). 큰 인스턴스에선 상향.
  - 테스트: `tests/test_stats_lowmem.py`(2) — 바뀐 함수 전부 호출(컬럼 누락=AttributeError 검출)+by_region 숫자 정확성. (총 110→112)
  - 검증: compileall PASS. ⚠️ pytest 실행은 머신에서(`uv run -m pytest -q`).
## v1.110 (2026-06-28)
- **render.yaml 무료 티어 대응**: 무료에서 미지원인 `preDeployCommand` 제거(마이그레이션은 배포 후 Shell에서 `db_upgrade` 1회 수동 안내). cron(매일 수집)도 무료 미지원이라 주석 처리(유료 전환 시 해제). 웹+Postgres만으로 무료 시작 가능하게 정리.
## v1.109 (2026-06-28)
- **Render 배포 준비(웹/PWA 출시)**.
  - `render.yaml` 블루프린트 추가 — 한 번의 Apply로 ① 웹 서비스(Docker, /health, JWT/ADMIN 자동생성, AUTH_DEV_LOGIN=false, 배포 시 `db_upgrade` 자동) ② 관리형 PostgreSQL ③ 매일 실거래 수집 크론(04:00 KST)을 함께 생성. 비밀값(MOLIT_SERVICE_KEY·CORS_ORIGINS)은 sync:false로 대시보드 입력.
  - `DEPLOY.md`에 Render 단계별 가이드(푸시→블루프린트→비밀값→마이그레이션 자동→첫 수집→도메인→PWA) 추가.
  - 기존 Dockerfile이 그대로 호환(멀티스테이지: 프런트 빌드→백엔드에 dist+WEB_DIR, `${PORT}` 대응) — 코드 변경 없음.
## v1.108 (2026-06-26)
- **버그 수정: `compare_one` NameError** (테스트가 검출). `app/services/stats.py`의 `compare_one`에서 `trade_count`가 정의되지 않은 `trades_recent`를 참조 → 실제 변수 `trades`로 수정. `/compare`(단지 비교) 요청 시 항상 터지던 실버그(다른 함수의 변수명이 잘못 복붙된 오타). 다른 함수(630행)의 `trades_recent`는 정상.
  - `test_compare.py::test_compare_one_metrics`·`test_compare_api` 가 잡아낸 것 — 컴파일로는 안 잡히는 런타임 버그를 테스트가 검출(테스트 추가의 가치).
## v1.107 (2026-06-26)
- **테스트 실행 경로 수정**: `pytest.ini`에 `pythonpath = .` 추가 — `pytest -q` 가 프로젝트 루트를 sys.path에 넣어 `app` 패키지를 찾도록(이전엔 `ModuleNotFoundError: No module named 'app'`). pytest 7+/8 지원 옵션. (코드 변경 없음·설정 한 줄)
  - 우회법: `python -m pytest -q` 또는 `PYTHONPATH=.` 도 동일 효과.
## v1.106 (2026-06-26)
- **회원 탈퇴(계정 삭제) — 실서비스/스토어 필수 기능**.
  - `DELETE /auth/account`(로그인+confirm 필수, **원자적 한 트랜잭션**). 설계(개인정보보호법·전자상거래법 고려):
    - **삭제**: 계정·기기연결·개인화(관심/최근/저장검색/설정)·좋아요/스크랩/신고·알림·푸시·내 매물·문의(받은+보낸).
    - **익명화**: 내 게시글/댓글 → 작성자 식별 제거(‘탈퇴한 사용자’)·스레드 보존.
    - **보존**: 구독/결제 기록(법정 보존의무)·동의 이력(적법성 증빙). ⚠️ 실 PG 도입 시 결제기록 보존정책 재점검 필요.
  - 프런트: 계정 메뉴에 ‘회원 탈퇴’(확인 다이얼로그→삭제→로그아웃·새로고침).
  - 처리방침: 권리 섹션을 ‘앱 내 회원 탈퇴로 즉시 삭제·게시글 익명화·법정 보존 예외’로 보강(두 복사본 동기화, 같은 2026-06-26 버전 내 보강이라 추가 재동의 없음). 스토어 메타에 ‘계정 삭제 제공’ 요건 충족 표기.
  - 테스트: `tests/test_account_delete.py`(4) — 401·400(confirm)·cascade+익명화·탈퇴 후 토큰 무효. (총 106→110)
  - 검증: 백엔드·테스트 py_compile·compileall PASS, 프런트 verify_frontend·괄호 균형 PASS. ⚠️ pytest 실행은 머신에서.
  - 문서: DATA·TESTING(R)·privacy(2벌)·store.
## v1.105 (2026-06-26)
- **초기 로딩·전송 최적화**(번들에 무거운 라이브러리가 없어 핵심은 압축·캐시).
  - **gzip 압축 미들웨어**(`GZipMiddleware`, minimum_size=600): JS/CSS/HTML/JSON 전송량 약 65~70%↓.
  - **정적 캐시 헤더**: SPA 마운트를 `_CachedSPA`로 교체 — 해시 자산 `/assets/*`는 1년 `immutable`, 그 외(index/manifest/아이콘)는 `no-cache`. `index.html`·`sw.js` 라우트도 `no-cache` 명시(업데이트 즉시 반영).
  - **Vite manualChunks**: React vendor를 별도 청크로 분리(앱 코드 변경 시 React 청크 캐시 유지).
  - 판단 근거: 의존성이 react+react-dom뿐(차트=SVG·지도 SDK=외부) → 파일 분할/코드 스플리팅은 위험 대비 실익 적음. 압축·캐시가 실질 지렛대.
  - 검증: 백엔드 compileall·vite.config 문법 PASS. ⚠️ 실제 효과(전송량·캐시 적중)는 머신에서 `npm run build`+DevTools로 확인(샌드박스는 빌드 불가).
  - 문서: DEPLOY(초기 로딩·전송 최적화).
## v1.104 (2026-06-26)
- **고도화 #1 레이트리밋 + #3 매출기능 테스트**.
  - **#1 보안**: `POST /inquiries`(연락처 포함 PII)와 `/billing/*` 가 레이트리밋 분류에서 빠져 있던 것을 추가 — 버킷 `inquiry`(6/분)·`billing`(20/분), config·.env.example 반영. 문의 스팸/PII 오남용 차단.
  - **#3 테스트**: `tests/test_inquiry.py`(8)·`tests/test_billing.py`(7) 신규(총 91→106). 문의=동의 필수·소유자만 연락처·404·타인차단·상태변경 권한·summary·401; 결제=feature_billing OFF 불변식(plans/me disabled·checkout/confirm/cancel 404)·플랜 구조·mock 토큰.
  - 검증: 백엔드·테스트 py_compile PASS. ⚠️ 샌드박스에 pytest/sqlalchemy 미설치 → 테스트 **실행 불가**, 통과는 머신 `pytest -q` 확인 필요.
  - 문서: TESTING(Q)·.env.example.
## v1.103 (2026-06-26)
- **지도 코드 리뷰 + 실서비스 보강**(렌더 불가 환경이라 정독 리뷰로 검수).
  - ① `stats.map_markers`에 `@stat_cached()` 적용 — 주 기능 지도가 트래픽이 많은데 매 호출마다 `_load`+전체 Complex를 재계산하던 것을 캐시(거래유형·유형별 키, 수집/지오코딩 시 자동 무효화).
  - ② `PriceMarkerMap` 언마운트 정리 추가 — idle 리스너 제거·마커 정리(탭 이동 시 unmounted setState 경고·리스너 누수 방지).
  - 리뷰 결과: 핵심 로직(무한루프·stale 클로저·Naver API 사용·빈데이터/좌표없음 처리)은 이상 없음 확인. 남은 관찰: viewport 목록 상위 300 캡(패널 카운트는 실수치)·구동 폴리곤/그리기 미구현(데이터·SDK 의존)은 의도된 범위.
  - 검증: compileall·verify_frontend·괄호 균형 PASS.
## v1.102 (2026-06-26)
- **지도 3단계 — 영역 단지 목록 시트 + 다중선택 비교**(기존 비교 인프라 재사용).
  - `AreaListSheet`: 지도에 보이는 영역의 단지를 가격순/이름순 목록으로(단지명·구/동·건수·대표가). 행 탭→단지 상세, ⊕→비교함 담기(`inCompare`/`toggleCompare`, 최대 4개). 담으면 기존 하단 비교 트레이→`CompareOverlay`(`/compare`)로 연결.
  - `PriceMarkerMap`의 `onViewport`가 보이는 마커 목록(items, 상위 300)도 보고 → `MapHub` "목록" 버튼으로 시트 오픈. 백엔드 변경 없음(`/map/markers`·`/compare` 재사용).
  - 무한루프 없음(effect 의존성 안정). 검증: compileall·verify_frontend·괄호 균형 PASS.
  - 보류(정직): **구·동 경계 폴리곤·freehand 영역 그리기**는 행정구역 GeoJSON·네이버 drawing SDK 의존이라 미구현 — 좌표 기반 뷰포트 영역 목록이 실질 대체. (ROADMAP 3단계 [~])
  - 문서: ROADMAP·TESTING(P).
## v1.101 (2026-06-26)
- **지도 2단계 — 뷰포트 "이 지역 평균" 패널 + 줌 클러스터링**.
  - `PriceMarkerMap` 재작성: 지도 idle(0.35s 디바운스)마다 보이는 영역 기준으로 **그리드 클러스터링**(줌아웃=묶음 "N곳"+중앙값, 줌인=개별 단지) + **뷰포트 요약**(곳 수·중앙값) 콜백. 묶음 클릭=줌인, 개별 클릭=단지 상세. 필터 변경 시 1회 fitBounds(패닝과 충돌 방지).
  - `MapHub`에 "이 지역" 패널(보이는 영역 곳 수·중앙값; 매매=평단가, 전세/월세=보증금). 백엔드 `map_markers`에 전체 summary(count/median/avg) 추가.
  - 설계: 청주 규모상 마커 1회 로드 후 뷰포트 요약·클러스터링은 클라이언트 처리(패닝마다 네트워크 호출 없음 → 빠르고 견고). 서버 bbox 로딩은 전국 확장 시 도입.
  - 무한루프 방지: render effect 의존성(markers/onViewport 참조) 안정 확인. 검증: compileall·verify_frontend·괄호 균형 PASS. (지도 상호작용은 NAVER 키+좌표로 머신 확인 필요)
  - 문서: ROADMAP(2단계 완료)·TESTING(O). 다음: 3단계(구·동 폴리곤·영역 검색·지도 비교).
## v1.100 (2026-06-26)
- **지도 주기능화 — 1단계(지도 전용 탭 + 가격 마커)**. 경쟁사(호갱노노·아실)처럼 지도를 주 진입점으로.
  - 하단 네비 6번째 **"지도" 탭** 신설. `MapHub`(거래유형·주택유형 필터) + `PriceMarkerMap`(네이버 SDK, 단지별 대표가 색 마커·클릭→단지 상세).
  - 백엔드 `stats.map_markers`(거래유형별 중앙값: 매매=평단가, 전세/월세=보증금 + 좌표, 가격대 분위 bands) + `/map/markers` 라우터. 좌표 미확인 단지 제외(왜곡 방지).
  - 마커 색=가격대 분위(5단계), 매매 라벨=평단가(만원/평)·전세/월세=보증금(억). 최근 집계 윈도우 기준 참고용 고지.
  - nav는 flex:1이라 6탭 자동 분배(레이아웃 변경 없음). map 아이콘 기존 보유.
  - 검증: compileall·py_compile PASS, 프런트 괄호 균형·verify_frontend PASS. (지도 렌더·엔드포인트 실제 동작은 NAVER_MAP_CLIENT_ID+좌표로 머신 확인 필요 — 샌드박스 불가)
  - 문서: ROADMAP(지도 주기능화 1·2·3단계)·TESTING(N). 다음: 2단계 bbox 뷰포트·클러스터링.
## v1.99 (2026-06-26)
- **검색 인덱스 — pg_trgm GIN(확장성)**. 선두 와일드카드 `LIKE '%q%'` 풀스캔 개선.
  - 마이그레이션 `0016_search_trgm`(head): PostgreSQL에 `pg_trgm` 확장 + GIN 인덱스(`gin_trgm_ops`) 5개(transactions.complex_name/dong_name, listings.title/complex_name/dong_name). **dialect 가드**로 SQLite는 no-op(스캔 폴백). 멱등(IF NOT EXISTS). 기존 `.like()`를 코드 변경 없이 가속.
  - 정합화: CLAUDE.md가 ④를 ✅로 표기했으나 ROADMAP/README는 "예정"이던 **불일치 해소** — 실제 구현하며 셋 다 완료(pg_trgm·0016·PostgreSQL)로 통일.
  - 운영 주의(DEPLOY): 관리형 DB는 `CREATE EXTENSION` 권한 필요, 대형 테이블은 CONCURRENTLY 수동 생성 옵션, 트라이그램 3글자↑ 선택도. 검증법(EXPLAIN)은 TESTING.md M.
  - 검증: compileall PASS, 마이그레이션 head 단일(0016). (인덱스 사용 여부는 운영 PostgreSQL에서 EXPLAIN 확인 필요 — 샌드박스 불가)
## v1.98 (2026-06-26)
- **개인정보처리방침 보강(문의 연락처·결제 반영) — 초안**.
  - privacy.md 1항(수집): 매물 **문의 연락처·내용**(동의 시 입력, 등록자에게 전달)·**결제 식별값**(PG 처리, 카드/계좌 미저장) 추가. 로그인 항목 문구 정합.
  - 2항(목적): 문의 전달·응대, 구독 결제·권한 관리 추가. 3항(보유·파기): 문의·결제 보유/파기 항목 추가(`[운영자 입력]` 보유기간). 4항(제3자): **"제3자 제공 안 함"→문의 연락처는 매물 등록자에게, 결제정보는 PG에 전달**로 정정(실제 동작과 일치).
  - app/web/legal·frontend/public/legal 두 복사본 동기화. `PRIVACY_VERSION` 2026-06-19→**2026-06-26 상향(동의 재수집)**.
  - 스토어 라벨 템플릿(google-play·app-store)에 문의 연락처(제3자 공유)·결제 항목 반영 안내 추가.
  - ⚠️ **법무 검토 필수**(본 문서는 초안·법률 자문 아님). 재수집을 원치 않으면 PRIVACY_VERSION 한 줄 되돌리면 됨. `[운영자 입력]` 항목(보유기간·PG명·연락처) 확정 필요.
  - 검증: legal.py py_compile PASS, 두 복사본 동일.
## v1.97 (2026-06-25)
- **결제/구독 스캐폴딩(첫 매출) — 전부 `feature_billing` OFF가 기본**(켜기 전엔 현재와 100% 동일).
  - 플래그 `feature_billing`(기본 false)·`billing_provider`(mock/toss/portone). `/config`에 billing 노출, 프런트 `FEATURES.billing`.
  - 모델 `Subscription` + 마이그레이션 `0015_subscription`(head). 서비스 `app/services/billing.py`(플랜 정의·provider 추상화·**mock**으로 키 없이 흐름 검증·toss/portone 스텁). `entitlement.is_premium`가 active 구독도 인정(플래그 ON 시).
  - API `/billing`(plans·me·checkout·confirm·cancel) — 전부 feature_billing ON일 때만, OFF면 404/enabled:false.
  - 리드 게이트(유료 가치): `/inquiries`가 **플래그 ON + 비프리미엄일 때만** 연락처 마스킹(`locked:true`, contact=null). OFF면 전체 노출(현재 동일). 대시보드에 🔒 표시 + "Pro 업그레이드"(mock 즉시 활성).
  - OFF 기본 불변식 확인: billing 404·plans disabled·마스킹 없음·업그레이드 버튼 숨김 → 현재와 동일.
  - 검증: 백엔드 compileall·py_compile PASS, 마이그레이션 head 단일(0015), 프런트 괄호 균형·verify_frontend PASS.
  - 문서: DATA(subscriptions)·README(모델)·ROADMAP·TESTING(L)·.env.example 갱신. (다음: 실 PG 키·웹훅 검증)
## v1.96 (2026-06-25)
- **문의/리드 기능(B2B 첫 매출 기반) — Phase 1**(모델·API·UI, 과금 게이트 OFF).
  - 모델 `Inquiry` + 마이그레이션 `0014_inquiry`(head). 소유자 비정규화(owner_account_id/owner_device_id)로 대시보드 조회 단순화.
  - API `/inquiries`: POST 생성(동의 필수·숨김/없는 매물 404), GET 목록(소유자만·연락처 포함), GET /summary(매물별 집계), POST /{id}/status(소유자만 new/read/contacted/closed). `account_from_auth` + device_id OR 매칭.
  - 프런트: 매물 상세에 `InquiryBox`("온라인 문의 남기기" → 이름·연락처·내용·동의 → 추적되는 리드 생성). 중개사 대시보드에 "받은 문의(리드)" 섹션·"받은 문의" Stat·매물별 문의 수·상태 버튼.
  - 개인정보: 연락처는 **소유자만 열람**·동의 필수·마케팅/제3자 제공 금지(9.A 준용). ⚠️ **개인정보처리방침에 '문의 연락처' 항목 추가 필요**(legal 검토·PRIVACY_VERSION·스토어 라벨) — 운영자/법무 후속.
  - 과금 게이트는 OFF(무료도 전체 열람). 다음 단계=결제(PG/구독) 연결 시 entitlement로 게이트.
  - 검증: 백엔드 compileall·py_compile PASS, 마이그레이션 head 단일, 프런트 괄호 균형·verify_frontend PASS.
  - 문서: DATA.md(inquiries)·README(모델)·ROADMAP·TESTING(K) 갱신.
## v1.95 (2026-06-25)
- **문서 전체 점검·정합화(코드 무변경)** — 핸드오버 문서를 현재 상태(v1.94)에 맞춤.
  - ROADMAP(SSOT): "출시 품질·수익화 토대(v1.65~v1.94)" 완료 섹션 추가(컷오버·PWA·접근성·페이지네이션·매물/중개사·출시도구). 수익화 스캐폴딩 상태 `[ ]`→`[x]`(OFF 기본), 프런트 빌드 항목 정본화 반영.
  - README: 프런트를 "Vite(main.jsx) 정본·app/web 동결·컷오버 구성 완료"로 수정(레거시 우선 서술 제거), 구조트리·컷오버 상태 갱신, TESTING.md·store/ 참조 추가.
  - CLAUDE.md: 검증 루틴을 frontend/src 정본 기준으로(app/web 편집 금지 명시), 프런트 서술 정합화, 중복 줄 정리.
  - QUICKSTART: Vite를 "UI 정본"으로 표기(레거시는 폴백·동결).
  - 점검 확인: 법적 문서 2벌(app/web·frontend/public) 동일 ✅, 문서 상호참조(.md/skills) 무결성 ✅.
## v1.94 (2026-06-25)
- **접근성 점검(대비·스크린리더 라벨) + 수정**.
  - 감사 결과: 색 대비(--ink/--muted/--teal/--up/--down)는 흰 배경·다크모드 모두 WCAG AA(약 5:1~14:1) 충족 → 색 변경 불필요. `lang="ko"`·`<img>` 없음(아이콘=인라인 SVG) 양호.
  - 아이콘 전용 닫기/지우기 버튼 6곳(× span): `aria-label`(닫기/검색어 지우기/사진 삭제) + `role/tabIndex/onKeyDown` 부여 — 스크린리더 명칭 + 키보드 조작 가능.
  - 폼 입력 라벨 연결: `LField`를 `<div>`→`<label>`로 변경해 모든 등록 폼 입력이 라벨과 프로그램적으로 연결(스크린리더가 "보증금(만원)" 등 읽음). 체크박스는 이미 label 래핑이라 양호.
  - 슬라이더(통근 시간/금리/기간)·숨김 파일 입력·댓글 수정 입력에 `aria-label` 추가. (aria-label 총 26)
  - 검증: 괄호 균형 · verify_frontend PASS. 잔여(경미): 장식용 › 셰브런(행 텍스트가 이름 제공)·매물 사진 배경이미지(인접 제목이 설명)는 후순위.
## v1.93 (2026-06-25)
- **PWA 앱 셸 캐싱 + 오프라인 셸 + 업데이트 배너**(의존성 없이 수제 SW).
  - sw.js 런타임 캐싱: navigate=네트워크 우선→캐시 셸(/)→offline.html, 정적 자산(/assets·/icons·manifest)=캐시 우선+백그라운드 갱신(SWR). **API 등은 미개입(항상 네트워크 — 시세 신선도·왜곡 방지)**. Vite 해시 자산이라 캐시 우선이 안전.
  - 버전드 캐시(`cj-shell-v2`), activate 시 구 캐시 정리. 푸시(push/notificationclick) 기능 보존.
  - 업데이트 배너: 새 SW 설치 감지 시 "새 버전이 준비됐어요 · 새로고침"(첫 설치 땐 미표시, `hadController` 가드). 운영 규칙=배포 시 sw.js VERSION 올리면 캐시 정리+배너 발화.
  - 문서: DEPLOY.md(PWA 전략·VERSION 규칙)·TESTING.md J 보강.
  - 검증: main.jsx 괄호 균형·verify_frontend PASS·sw.js node -c PASS. (런타임은 운영자 브라우저 확인 필요)
## v1.92 (2026-06-25)
- **접근성(키보드) 마무리** — 남아있던 인라인 클릭 행 전부 전환.
  - 검색 결과(지역·단지·매물), 검색홈·비교 단지 검색, 예산·통근 결과, 시세 단지목록·랭킹·거래·그룹토글, 청약 위젯 등 클릭 가능한 txrow/listrow 16곳에 `tabIndex/role="button"/onKeyDown=onEnter` 적용. 조건부(clickable) 행은 조건부로 부여.
  - 버튼과 핸들러가 겹치는 곳은 고유 앵커로 분리해 **이중 실행(키보드 중복 발동) 방지**. 네이티브 `<button>`에는 onKeyDown 미부여.
  - 결과: 키보드 미적용 클릭 행 0. (role/onKeyDown 다수)
  - 검증: 괄호 균형 · verify_frontend PASS.
## v1.91 (2026-06-25)
- **접근성 2차(키보드) + 빈 상태 CTA 확대**.
  - 키보드 네비게이션: 클릭 가능한 div를 키보드로 조작 가능하게(`tabIndex/role="button"/onKeyDown=onEnter`). 적용: 재사용 컴포넌트 ListingCard·PostCard·TourStop(→ 모든 매물/게시글/임장 단지), 홈 배너(거래 급상승·대장 아파트·최근 본 단지), 랭킹/최근 시트 행. (role 28·onKeyDown 18) Enter/Space로 열림 + v1.90 focus-visible로 포커스 표시.
  - 빈 상태 CTA 추가: 게시판 0건 → "+ 글쓰기"(비로그인 시 로그인 유도), 시세 검색 무결과(q) → "검색 지우기". (Empty action 2→5곳)
  - 검증: 괄호 균형 · verify_frontend PASS.
  - 남은 작업(정직): 검색결과·상세 등 흩어진 인라인 txrow/listrow 일부는 미전환 — 후속 마이크로 패스 대상.
## v1.90 (2026-06-25)
- **출시 품질 다듬기(접근성·빈상태·오프라인)**.
  - 접근성: 전역 `:focus-visible`(teal 2.5px 외곽선) 추가 — 키보드 포커스 가시성(WCAG 2.4.7). `prefers-reduced-motion` 시 애니메이션/트랜지션 최소화. (focus-visible 0→적용)
  - 빈 상태 CTA: 매물 목록이 0건일 때 "+ 매물 등록" 버튼을 빈 화면에 노출(`Empty` action 슬롯 활용, setMode in scope). ※ "표본 부족"류 빈 상태는 사용자 행동이 무의미해 제외.
  - PWA 오프라인 폴백: `frontend/public/offline.html`(정적 안내 페이지) + sw.js에 fetch 핸들러 추가. **navigate 요청만** 네트워크 우선·실패 시 오프라인 페이지 폴백. 자산·API는 가로채지 않아 스테일/업데이트 위험 없음. install 시 offline.html 1개만 캐시, activate 시 구 캐시 정리. (기존 push 기능 보존)
  - 검증: main.jsx 괄호 균형 · verify_frontend PASS · sw.js `node -c` PASS. TESTING.md J 섹션(브라우저/기기 확인법) 추가.
  - 적용 범위: frontend(dist) 기준. 레거시 app/web은 동결.
## v1.89 (2026-06-25)
- **UI 버그 5건 일괄 수정**(사용자 리포트).
  - ① 면적 단위(평/㎡) 연결: 단지상세 면적별 정보가 평으로 안 바뀌던 문제. 원인은 `unit==="pyeong"`(실제 값 `"py"`)라 조건이 항상 거짓. `areaTxt(a,unit)` 헬퍼 추가해 AreaSection 제목·전용 평형 텍스트·대출 면적 버튼·전세안전 기준 등 5곳을 `fmtArea(a.area,unit)` 기반으로 통일(평/㎡ 전환됨). ※ 소형/중형/대형 밴드 라벨(~60㎡)은 표준 범주라 유지. `res.affordability.label`은 면적 객체가 아니라 제외.
  - ② 단지상세 가로 스크롤 제거: 시트 콘텐츠 영역에 `overflowX:hidden`(SheetShell·Sheet 공통). 세로 스크롤·maxWidth 480 유지라 내용 손실 없음.
  - ③ 거래 급상승·대장 아파트 시트가 짧게 뜨던 것 수정: `Sheet`에 `fill`(height 93vh) 옵션 추가 → 통근(SheetShell)처럼 풀 높이로. RankSheet에 적용.
  - ④ 최근 본 단지를 거래 급상승처럼 표시: 기존 Collapsible 목록 → 배너+풀시트(RecentList 재작성).
  - ⑤ 거래 급상승·최근 본 단지 클릭 시 최대 10개: RankSheet·RecentList 모두 `slice(0,10)`.
  - 검증: 괄호 균형 · verify_frontend PASS. (프런트 변경은 npm run dev/build 후 반영)
## v1.88 (2026-06-25)
- **시세 단지 리스트 페이징 누락 수정**(v1.76에서 빠졌던 부분 — 사용자 지적).
  - 시세(PriceHub) **단지 목록(overview)** 이 전체 렌더되던 것을 `MoreList`(12개씩 더보기)로.
  - 같은 화면 **검색결과 단지 목록**도 `MoreList`(10개씩)로 일관 적용.
  - 이로써 긴 리스트 더보기 적용 누적: 매물(서버 페이지네이션)·청약·단지상세 최근거래·시세 거래그룹·시세 단지목록·시세 검색결과.
  - 검증: 괄호 균형 · verify_frontend PASS · MoreList 5곳.
## v1.87 (2026-06-25)
- **출시 준비(Phase 0) 코드 갭 보강**.
  - `scripts/preflight.py` 신설 — '인터넷 노출 안전성' 점검(JWT_SECRET 강도·ADMIN_TOKEN·CORS 와일드카드·DATABASE_URL·MOLIT 키·SPA 빌드·법적 페이지·아이콘 플레이스홀더). 앱 의존성 없이 동작(os.environ+.env+파일), FAIL 시 종료코드 1(파이프라인 게이트). doctor.py(데이터·시스템 헬스)와 역할 분리. 샌드박스 실행 검증(빈 설정→FAIL 1·WARN 7 정확 감지).
  - `store/` 스토어 메타데이터 템플릿 신설 — google-play.md·app-store.md(등록 문구·카테고리·키워드·Data safety/App Privacy 라벨 초안·심사 메모) + README(자산 체크리스트). 개인정보 라벨은 실제 동작 검증 필수임을 명시(특히 대출 9.A).
  - LAUNCH.md Phase 0에 preflight·store 사용 연결.
## v1.86 (2026-06-25)
- **출시→매출 단계 전략 문서(LAUNCH.md) 신설** — 코드 변경 없음.
  - Phase 0 출시준비(운영자 셋업·런타임 검증) → 1 웹/PWA 무료출시 → 2 스토어 앱 → 3 B2B 중개사 유료(첫 매출) → 4 소비자 프리미엄 → 5 제휴 → 6 광고.
  - 각 단계: 할 일·담당(운영자🧑‍💼/코드💻)·전환 KPI·비용. 가드레일(핵심 무료·값 불변·신뢰 우선·규제 자문)·정직한 한계 명시.
  - 핵심 순서: 무료로 신뢰·트래픽 먼저, 그 위에서 단계적 수익화. 첫 매출은 B2B 중개사가 가장 현실적.
  - README 포인터 추가.
## v1.85 (2026-06-25)
- **중개사 대시보드 v2-B: 매물 수정(PUT)**.
  - 백엔드: `PUT /listings/{id}`(owner-only). ListingIn 폼 항목만 갱신 → **status/views/is_sponsored/등록일/소유자는 보존**. `GET /{id}`은 숨김 매물도 **소유자면 조회 가능**(편집·복구용), 타인은 404.
  - 프런트: `ListingForm`에 `initial` 프롭(편집 초기화) + 저장 시 **PUT 분기**, 헤딩("매물 수정")·버튼("수정 저장") 라벨 대응. 대시보드 각 매물 "수정" 버튼 → 상세 GET으로 전체 필드 로드 후 폼 편집 → 저장 시 목록 자동 갱신.
  - 일반 등록 흐름(ListingsTab)은 그대로(initial 없으면 POST).
  - 검증: app+migrations 컴파일 OK · verify_frontend PASS · 괄호 균형.
- 정직한 한계: 문의/리드(고객 연락) 추적은 아직 없음 → v3 후보(문의 모델·연락 버튼·집계).
## v1.84 (2026-06-25)
- **중개사 대시보드 v2-A: 조회수 추적 + 상태관리**.
  - 백엔드: `Listing.views` 컬럼(마이그레이션 `0013_listing_views`). 상세 `GET /{id}`가 **외부 조회만 +1**(소유자 본인 조회는 제외 — 정직한 집계). `_row_full`에 `views` 노출.
  - 상태 변경 API `POST /listings/{id}/status`(owner-only, active/traded/hidden). 목록 API에 `manage=1`(소유자 관리목록=전체 상태) 추가 — **공개·일반 내매물 목록은 활성만 그대로 유지**.
  - 프런트 대시보드: **총 조회수·매물별 조회수** 표시, 상태관리 버튼(거래완료↔판매중, 숨김↔복구). 영구삭제 대신 **되돌릴 수 있는 상태 기반 관리**.
  - 검증: app+migrations 컴파일 OK · verify_frontend PASS · 괄호 균형.
## v1.83 (2026-06-25)
- **중개사 대시보드 v1(B2B 수익화 1순위 기능)** — 프런트 단독, 있는 데이터 기반(지표 미조작).
  - `AgentDashboard` 시트(SheetShell): 계정 메뉴에서 **role=agent에게만** "📊 중개사 대시보드" 진입.
  - 요약: 총 매물·활성 수·거래유형(매매/전세/월세) 분포·지역(구) 분포. `feature_ads` ON이면 "광고 노출" 수도 표시.
  - 내 매물 관리: `/listings?mine=1` 로 불러와 카드 목록(거래/가격/상태[거래완료·숨김]/광고 배지/등록일), **행 탭→매물 상세**(openListingId), **삭제**(전파 차단), **+ 매물 등록**(매물 탭 이동).
  - 접근성: 닫기 aria-label/키보드, 삭제 aria-label.
  - 검증: 괄호 균형 · verify_frontend PASS · 탭 키 listing 정합.
- 정직한 한계: **조회수·문의(리드) 추적은 백엔드에 없음** → v2로 분리(Listing.views 컬럼+상세 GET 증가+마이그레이션, 문의 모델 필요). 매물 수정(PUT) 미구현이라 관리에 삭제·재등록만.
## v1.82 (2026-06-25)
- **수익화 스캐폴딩(부록B) — 전부 피처 플래그 뒤, 기본 OFF=현재 동작 100% 동일(첫 출시 제외 가능)**. 구조/기능 테스트용.
  - 모델: `listings.is_sponsored`(bool·기본 false)·`priority`(int·0), `accounts.plan`(free|premium). 마이그레이션 `0012_monetization`(additive·멱등·server_default).
  - 매물 목록: 응답에 `is_sponsored`/`priority` 포함. 정렬은 **`feature_ads` ON일 때만** 후원·우선순위 우선(OFF면 최신순 그대로).
  - 권한: `app/services/entitlement.py`(`is_premium`/`require_premium`). `feature_monetization` OFF이면 항상 free. `/auth/me`(_acc)에 `plan`·`is_premium` 노출. **기존 기능은 아무것도 게이팅 안 함(구조만)**.
  - 프런트: `/config`의 `feature_flags`를 `FEATURES`로 읽어, ListingCard에 **"광고" 배지(amber)** = `FEATURES.ads && x.is_sponsored`일 때만.
  - 테스트용 admin: `POST /admin/test/sponsor`(매물 광고 토글)·`POST /admin/test/plan`(계정 plan) — admin_token 보호.
  - 객관성 가드레일: sponsored는 **표시 순서·배지만**, 시세/추천 값은 불변.
  - 문서: MONETIZATION.md 부록 반영, TESTING.md §H(테스트 절차), CLAUDE.md 상태.
  - 검증: app+migrations 컴파일 OK · verify_frontend PASS · 플래그 기본 OFF 확인.
## v1.81 (2026-06-25)
- **수익화 전략 문서(MONETIZATION.md) 신설** — 코드 변경 없음(전략 정리).
  - 기능 중심 전략: 핵심 데이터는 무료 유지, A)중개사 B2B(최우선·신뢰위험 낮음) → B)소비자 프리미엄 구독 → C)제휴(대출/이사, 고규제) → D)익명 집계 데이터 → E)광고(최후).
  - 현재 구조 근거 명시: `/config` 피처플래그(ads·monetization, 기본 OFF)·agent role은 있음 / sponsored·entitlement·결제는 없음.
  - 객관성 가드레일: sponsored는 표시 순서·배지만, 시세/추천 값 불변. 제휴·광고 명확 표기. 금융 제휴 법무 검토.
  - 단계 로드맵(Phase 0 무료 출시 → 1 B2B → 2 프리미엄 → 3 제휴 → 4 광고), 부록 B 정합 스캐폴딩 후보 정리.
  - README에 포인터 추가.
## v1.80 (2026-06-25)
- **접근성 1차(②-3)** — 큰 단일 파일 전면 개편 대신 안전·고효과 항목 중심.
  - Icon 컴포넌트 전역에 `aria-hidden=true`·`focusable=false` → 모든 장식 아이콘을 스크린리더가 건너뜀(SR 경험 개선).
  - 닫기(×) 버튼 3곳 + 홈 진입 카드 3개(통근·예산·대출)에 `aria-label`·`role="button"`·`tabIndex={0}` + **Enter/Space 키보드 활성화**(`onEnter` 헬퍼). 마우스 없이 조작 가능.
  - 하단 네비에 `role="navigation"` `aria-label`.
  - 온보딩 환영 카드 닫기에도 aria-label(이미 적용).
  - 검증: 괄호 균형 · verify_frontend PASS · aria-label 4→12 · onKeyDown 6.
  - ⚠️ 정직한 범위: 전면 WCAG 감사(모든 클릭 div 키보드화·색 대비·focus-visible·실제 스크린리더 테스트)는 더 큰 후속 작업으로 남김.
## v1.79 (2026-06-25)
- **온보딩(②-2, 첫 방문 안내)**. 통근·예산·대출 같은 숨은 강력기능의 발견성 개선.
  - 홈 최상단에 **첫 방문 시에만** 뜨는 dismissible 환영 카드. "통근시간으로/예산으로/대출 한도" 칩을 눌러 해당 시트로 바로 진입.
  - × 로 닫으면 `safeStore`(`cj_onboard_v1`)에 기록해 다시 표시 안 함. 모달이 아니라 카드라 흐름을 막지 않음.
  - 검증: 괄호 균형 · verify_frontend PASS.
## v1.78 (2026-06-25)
- **대출 진입 노출(②-1, 발견성 개선)**. 핵심 차별화인 대출 계산이 단지상세에만 묻혀 있던 문제 해결.
  - 홈에 "내 대출 한도 계산" 진입 카드 추가(통근·예산 카드와 동일 패턴/스타일).
  - `LoanSheet` 오버레이 신설(BudgetSheet 미러링, SheetShell) → 카드 탭 시 전체 시트로 대출 계산기 표시. `Loan`은 단독 모드(직접 매매가 입력) 동작.
  - App 배선: `loanOpen` 상태, Board에 `onLoan` 전달, 네비 숨김 조건에 추가, 단지 추천 시 `openComplex` 연결.
  - 뉴스·정책: 이미 홈 '오늘의 정보'(defaultOpen)에 노출되어 별도 작업 없음.
  - 검증: 괄호 균형 · verify_frontend PASS · LoanSheet 정의1/사용1.
## v1.77 (2026-06-25)
- **매물 리스트 서버 페이지네이션 실연결**(v1.76의 백엔드 offset 소비).
  - ListingsTab: 페이지 크기 20. 필터 변경 시 `offset=0` 리셋 후 로드, "더보기"는 `offset=현재개수`로 다음 페이지를 받아 **append**(누적). 응답 `has_more`로 더보기 노출 제어, 로딩 중 "불러오는 중…" 표시. 데모 폴백 시 더보기 비노출.
  - 매물은 클라이언트 더보기(MoreList) 대신 **서버 더보기**로 전환(50 캡 너머 수신). 한정 데이터인 청약·단지상세 최근거래·시세 거래그룹은 MoreList(클라이언트 더보기) 유지.
  - 필터 파라미터를 `filterParams()`로 분리해 load/loadMore가 공유(중복 제거).
  - 검증: 괄호 균형 · verify_frontend PASS · MoreList 사용 3 · has_more 소비 3.
## v1.76 (2026-06-25)
- **긴 리스트 페이징(UI 보강) + 백엔드 페이징 준비**.
  - 프런트(단일 소스 `frontend/src/main.jsx`): 재사용 `MoreList`(더보기·증분 로드) 추가 → **매물·청약·단지상세 평형별 최근거래·시세 거래그룹**에 적용. 처음 4~6개만 렌더하고 "더보기 (남은 N개)"로 step씩 추가 → 모바일 길이·렌더 DOM 부담 동시 개선. 리스트 변경 시 자동 초기화.
  - 기존에 이미 페이징되던 것(랭킹 RankSheet·시세 BandList 그룹 8/페이지)은 유지. 중복 페이저 없이 보완.
  - 백엔드(레거시·dist 공통): `/transactions`·`/listings`에 **`offset` 파라미터 추가(기본 0 = 동작 불변)** + 응답에 `offset`·`has_more` → 50개 캡 너머도 "다음 페이지"로 분할 수신 가능(사용자 요청한 "백엔드에서 나눠 보내기" 준비). 응답은 기존 `{items,count}`에 필드만 추가(하위호환).
  - 합리적 설계: 프런트 더보기가 렌더 부담을 먼저 해소(≤50 캡 내), 데이터가 50을 상시 초과할 때 프런트가 `offset`로 다음 페이지를 이어받는 2단 구조.
  - 검증: app 컴파일 OK · verify_frontend PASS · 괄호 균형 · MoreList 정의1/사용4.
## v1.75 (2026-06-25)
- **컷오버 확정 — 프로덕션이 Vite dist를 서빙, 소스 단일화**.
  - **Dockerfile 멀티스테이지화**: ① node로 `frontend` 빌드 → ② 백엔드 런타임에 `dist` 포함 + `ENV WEB_DIR=/app/frontend/dist`. 즉 배포 이미지가 레거시가 아닌 **빌드된 dist를 서빙**(컨테이너가 컷오버를 보장). 빌드 머신엔 Docker만 있으면 됨(npm 단계 내장).
  - **단일 소스 전환**: 웹 UI 권위 소스 = `frontend/src/`. 레거시 `app/web/index.html`은 **동결(편집 금지)**, bare 로컬 폴백으로만 잔존(한 사이클 후 제거 예정).
  - `scripts/verify_frontend.py`: 레거시 대조를 **동결 참조(정보용)**로 완화(향후 단일소스 편집으로 차이 증가 정상), main.jsx 구조 검증(괄호·import·index.html)은 하드 유지. 레거시 없어도 동작.
  - 문서: `CUTOVER.md`(확정 상태·단일소스·컨테이너 검증), `CLAUDE.md`(단일소스 관례), `DEPLOY.md`(멀티스테이지·/assets), `ROADMAP.md`(항목3 [x]).
  - 검증: app 컴파일 OK · verify_frontend PASS(단일소스 모드) · Dockerfile 스테이지/dist/WEB_DIR 확인.
  - ⚠️ 남은 1개 미검증: 샌드박스 도커 빌드·기동 불가 → **운영 머신에서 컨테이너 띄워** 라우트·/assets·/health 1회 확인(CUTOVER.md 체크리스트). 통과 시 컷오버 完了.
## v1.74 (2026-06-25)
- **배포·운영 필수 구성**(기본 동작 불변, 추가/문서 위주).
  - **Dockerfile** 신설(python:3.12-slim, 비루트 appuser, `uvicorn --workers ${WEB_CONCURRENCY:-2}`) + **.dockerignore**(.env·산출물 제외). compose가 참조하던 누락 이미지 해소.
  - **docker-compose.prod.yml** 신설: web(다중 워커)+scheduler(단일, 중복수집 방지)+Postgres. 기존 dev compose는 그대로.
  - **CORS 환경변수화**(`app/main.py`): `CORS_ORIGINS` 콤마구분, 미설정 시 `*`(개발 불변). 운영은 도메인+앱 origin으로 좁힘.
  - **DEPLOY.md** 신설: 아키텍처·필수 환경변수 표·빌드/실행(compose, alembic upgrade)·Nginx HTTPS·배포 전 점검 체크리스트·운영(스케줄러 단일·백업·모니터링·롤백)·보안 체크.
  - `.env.example`에 `CORS_ORIGINS`·`WEB_DIR`·`WEB_CONCURRENCY` 추가. README·ROADMAP·CLAUDE 동기화.
  - 검증: app 컴파일 OK · CORS 로직(기본 `*`/운영 좁힘) · compose YAML 유효(db/web/scheduler) · Dockerfile 비루트 · verify_frontend PASS(프런트 무영향).
  - ⚠️ 정직한 한계: 샌드박스(네트워크 X)에서 **이미지 빌드·기동은 미검증** → 운영 머신에서 `DEPLOY.md` 절차로 확인.
## v1.73 (2026-06-25)
- **에러바운더리 추가**(첫 기능 보강 — 안정성). 컴포넌트 렌더 오류 시 **전체 백스크린 대신 "일시적인 오류" 카드 + 새로고침**. 정상 동작 시 UI 변화 없음(순수 추가).
  - 첫 클래스 컴포넌트(`ErrorBoundary extends React.Component`, getDerivedStateFromError/componentDidCatch) — 레거시(Babel)·main.jsx(실 React) 양쪽 동작. 참조 색상은 모듈 상수(INK/MUTED/TEAL, var(--*)).
  - 루트 렌더를 `<ErrorBoundary><App/></ErrorBoundary>`로 래핑.
  - **컷오버 전이라 레거시·main.jsx 양쪽에 동일 반영** → 둘의 1줄 차(API) 불변 유지(verify_frontend PASS, 본문 3706=3706). 괄호 균형·상수 정의 확인.
  - 참고: 이번이 첫 의도적 기능 변경 → 레거시 `app/web/index.html`은 더 이상 v1.65 원본(/tmp/orig)과 동일하지 않음. 이후 무결성 기준은 verify_frontend(main.jsx↔현 레거시 1줄 차).
  - TESTING.md D에 에러바운더리 확인 항목 추가.
## v1.72 (2026-06-25)
- **컷오버 준비 — 레거시 HTML → Vite dist 서빙 전환 토대**(기본 동작 100% 불변).
  - `app/main.py`: `WEB_DIR` 환경변수화(기본=`app/web` 그대로). `WEB_DIR=frontend/dist`(assets/ 보유)일 때만 `SPA_MODE` → SPA 정적 마운트(`/assets`·manifest·icons). env 지정해도 assets 없으면 비활성(안전장치). 명시 라우트·API 라우터가 우선 매칭되어 가려지지 않게 마운트는 파일 끝에 추가.
  - `CUTOVER.md` 신설: 전환 절차(build → `WEB_DIR=...dist` → 재시작) · 런타임 검증 체크리스트 · **즉시 롤백(`unset WEB_DIR`, 코드 변경 0)** · 컷오버 후 소스 일원화(`frontend/src/` 단일) · 모듈 분리 가이드.
  - 문서 동기화: `CLAUDE.md`(WEB_DIR·CUTOVER 포인터), `TESTING.md`(E-2 컷오버 검증 절), `ROADMAP.md`(항목3 컷오버 준비 완료).
  - 검증: app/ 컴파일 OK · WEB_DIR/SPA_MODE 로직(기본 비활성·dist 활성·assets없음 비활성) 확인 · 레거시 index.html 원본 동일 · verify_frontend PASS.
  - ⚠️ 정직한 한계: 샌드박스에 fastapi 미설치 → **런타임 서빙 동작은 개발 머신에서** `CUTOVER.md` 절차로 확인 필요(여기선 문법·전환 로직만).
## v1.71 (2026-06-24)
- **테스트 방법 기록 + 실행 가능한 검증 도구**(앱 동작 변경 없음 — 테스트 툴/문서만).
  - `TESTING.md` 신설: 전 레이어 테스트 방법 단일 기록 — 어디서 무엇을 도는지(샌드박스/PC/실기기/Mac), A 백엔드·실데이터(doctor·verify_region_codes·run_collect·/health·/status/data), B 회귀(pytest·compileall·CI), C 오프라인 무결성(verify_frontend·레거시 괄호스캔), D 프런트 빌드(npm + UI 체크리스트), E PWA(DevTools Application·설치), F Capacitor/Android(CAPACITOR.md 연계), G Phase D 예정, 릴리스 전 체크리스트.
  - `scripts/verify_frontend.py` 신설: `python -m scripts.verify_frontend` — main.jsx 본문이 레거시와 **API 1줄만 다름** + 괄호 균형 + React/ReactDOM import 커버 + index.html(CDN 제거·module·root·manifest·SW) 자동 확인. 실행 PASS 확인됨.
  - `CLAUDE.md` §6에 verify_frontend·TESTING.md 포인터 추가.
  - 비파괴: 레거시 `app/web/index.html` 원본 동일, `frontend/src/main.jsx` 본문 1줄차(불변) 재확인.
## v1.70 (2026-06-24)
- **모바일 앱 Phase C — Capacitor 셸 스캐폴딩**(설정·런북만. 네이티브 `android/` 생성·빌드는 개발 머신에서).
  - `frontend/capacitor.config.json`(webDir=dist·appId placeholder·SplashScreen), package.json에 `cap:sync/android/ios` 스크립트.
  - `frontend/.env.production.example`(네이티브 빌드용 `VITE_API_BASE` 절대 URL — 같은 출처가 아니므로 필수), `.gitignore`에 `.env.production`·`/android`·`/ios`.
  - `frontend/CAPACITOR.md` 런북: 선행조건(A/B 빌드 성공)·설치(최신)·appId 확정·`cap add android`·네이티브 빌드(API base)·sync/open·**노치 세이프에어리어 CSS(런북에만, 미적용)**·CORS·아이콘/스플래시·다음(D iOS/푸시·E 심사·F OTA).
  - 비파괴: 레거시·백엔드·`main.jsx` 본문·`frontend/index.html` 무변경(세이프에어리어는 자동 적용 안 하고 런북에 명시 → 기기 검증 후 적용).
  - ⚠️ 이 환경에선 `npx cap add android`·Gradle 빌드 불가(Android SDK·네트워크 필요) → 실제 네이티브 빌드는 개발 머신. Capacitor는 A/B 빌드 검증 후 진행.
## v1.69 (2026-06-24)
- **문서 동기화(드리프트 제거)** — 코드 변경 없음, 기존 서술 보존 + 구조·상태만 정확 반영.
  - `README.md`: 기술스택 표에 `frontend/` Vite 빌드 추가, 프로젝트 구조 트리에 `frontend/` 추가, 구조점검 표 ①(프런트 빌드) 상태를 Phase A·B 완료로 갱신 + `MOBILE_APP_STRATEGY.md` 안내.
  - `QUICKSTART.md`: **폐기된 Expo(`cheongju-mobile`) 안내 교체** → 새 프런트(Vite) 실행·빌드 섹션 + 네이티브(Capacitor) 안내.
  - `ROADMAP.md`: 프런트 빌드(프로덕션준비 3·6대구조 ①) 상태 갱신, M5 앱 항목을 "RN 폐기→Capacitor 확정, Phase A·B 완료, C~F 남음"으로 정정.
  - `CLAUDE.md`: 스택에 frontend 빌드(마이그레이션 중) **인수인계 규칙**(레거시가 권위·컷오버 전 수정 위치·비파괴 원칙) 추가, 레포 트리에 `frontend/`, 현재상태에 Phase A·B 완료 + Capacitor 확정 반영.
  - 검증: 레거시 `app/web/index.html` 원본과 동일, `frontend/src/main.jsx` 본문 1줄차(불변) 재확인.
## v1.68 (2026-06-24)
- **모바일 앱 Phase B — 설치형 PWA**(비파괴: `frontend/`에만 추가, 레거시·백엔드·`main.jsx` 본문 무변경).
  - `frontend/public/manifest.webmanifest` 추가(name·short_name·start_url·display=standalone·theme_color #0F766E·background #fff·아이콘 3종 any/maskable).
  - 아이콘 생성: `icon-192/512`, `icon-maskable-512`(안전영역 패딩), `apple-touch-icon-180`(브랜드 틸 + 상승추이 마크). ⚠️ 기능용 기본 아이콘 — 스토어 제출 전 디자인 교체 권장.
  - `frontend/index.html` head에 manifest·theme-color·apple-touch-icon·apple PWA 메타·favicon 추가, body에 **로드 시 서비스워커 등록 스크립트**(설치형 요건; 기존 푸시 코드의 register와 멱등). main.jsx는 손대지 않음.
  - 서비스워커(`sw.js`)는 푸시 전용 그대로 유지(설치 가능성엔 매니페스트+아이콘+등록 SW로 충분). 오프라인 캐싱은 후행 선택.
  - 검증(오프라인): manifest JSON 유효·필수필드·maskable 포함, 아이콘 4종 생성·크기 확인, index.html 삽입 확인, main.jsx 본문 1줄차(불변), 레거시 동일.
  - ⚠️ 실제 설치 가능 여부(Android 크롬 "홈 화면에 추가" 독립실행, iOS 사파리 설치)는 **HTTPS 환경 + 실제 빌드**에서 확인 필요. 네트워크 차단으로 여기선 빌드 미실행.
## v1.67 (2026-06-24)
- **모바일 앱 Phase A — Vite 빌드 토대(`frontend/`) 추가**(비파괴: 기존 `app/web/index.html`·백엔드 무변경).
  - 목적: 브라우저 런타임 Babel + CDN 의존 제거 → `npm run build`로 `dist/` 산출(스토어/Capacitor의 공통 선행조건).
  - `frontend/src/main.jsx` = 기존 인라인 스크립트 **본문 무변경**(원본 대비 diff 결과 **딱 1줄**만 차이: `const API="";` → `import.meta.env.VITE_API_BASE` 폴백 `""`). 상단에 `import React`/`createRoot`(react-dom/client)/`createPortal`(react-dom) 추가.
  - `frontend/index.html` = React/ReactDOM/Babel CDN 제거 + module 스크립트. Pretendard는 Phase B에서 번들(현재 CDN 유지).
  - `package.json`(react 18.2.0·vite 5·@vitejs/plugin-react 4) / `vite.config.js` / `.env.development`(dev API base) / `README.md`(빌드·검증·컷오버 가이드).
  - 검증(오프라인 가능 범위): 본문 무변경 diff, 괄호 균형, React/ReactDOM 사용처가 import로 전부 커버됨(특히 `createPortal` 누락 버그를 사전 발견·수정), 외부 빌드 의존 없음(네이버 지도는 런타임 주입, 카카오는 OAuth 설정값).
  - ⚠️ 네트워크 차단 환경이라 `npm install`/`npm run build`는 **미실행** → 개발 머신에서 README 체크리스트로 최종 확인 필요. 검증 후 컷오버(레거시 index.html 제거).
## v1.66 (2026-06-24)
- **버그픽스(치명) — 홈 대시보드 데드락 제거**: `stats.trending_complexes`('거래 급상승')에 `@stat_cached()` 데코레이터가 **두 번** 적용돼 있던 문제를 한 줄 제거로 수정.
  - 원인: stat_cached 캐시 키는 `fn.__qualname__` 기준이라 두 겹이 **같은 키**를 공유. 캐시 미스 시 바깥 wrapper가 그 키의 **비재진입 락**을 잡은 채 loader로 안쪽 wrapper를 호출 → 안쪽이 같은 락을 재획득하려다 **데드락**. 영향: `GET /dashboard/board`(앱 첫 화면)가 데이터 버전마다 첫 요청에서 정지.
  - 회귀 방지: `tests/test_stats_decorator.py`(app 전체 '연속 동일 데코레이터' 0건 구조검사 + trending_complexes 데드락 워치독).
  - 이 버전은 원본 v1.65에 위 버그픽스만 적용한 것입니다. (검토 과정에서 시험했던 전월세 전환율 관련 추가분은 전부 제거하고 원래 홈 화면 기능·UI를 그대로 복원했습니다.)
## v1.65 (2026-06-22)
- **공유·SEO 진입 페이지(사용자 획득) — SPA 영향 없음**: 백엔드가 서버 렌더 진입 페이지를 추가 제공.
  - `GET /r/{lawd_cd}`(지역 시세 요약)·`/c/{lawd_cd}/{name}`(단지 시세) — `<title>`·description·**Open Graph/Twitter 메타**(카카오톡·검색 미리보기) + 핵심 시세(중앙값·전세가율·거래수) + 주요 단지 링크 + '앱에서 보기' CTA. 데이터 없으면 '수집 중' 안전 표기, 모든 동적 문자열 html.escape(인젝션 방지).
  - `GET /sitemap.xml`(지역+주요 단지 최대 30/구)·`/robots.txt` — 검색엔진 색인.
  - stats.price_overview·complex_detail 재사용. 절대 URL은 PUBLIC_BASE_URL(없으면 요청 호스트 추론). SPA(/) 및 기존 API 불변.
  - 효과: ① 구글 색인(검색 유입) ② 카톡 공유 리치 미리보기 ③ 재작성 없이 발견·공유 통로 확보. 테스트 tests/test_landing.py. .env.example·skills·ROADMAP 동기화.
## v1.64 (2026-06-22)
- **데이터 파이프라인 견고화(실데이터 launch 대비) — 기존 동작 영향 없음**: 정규화 필드 미매핑을 '조용히'가 아니라 '시끄럽고 자가진단되게'.
  - `molit/normalize.py`에 선택적 `NormalizationReport` 추가. `normalize_row(..., report=r)`로 넘길 때만 핵심 필드 미매핑(deal_amount/contract_date/exclusive_area/complex_name) 집계 + 원본 키 샘플 보존. **report 미전달 시 반환·로직 완전 동일**(기존 호출부 무영향). 유형별 오탐 방지(전월세·단독다가구 제외).
  - `collect_live` 가 수집 중 report 누적 → 반환 `mapping`·last_collect.mapping_misses·미매핑 시 단일 WARNING. JobRun.stats(/admin/runs)에서 확인.
  - `scripts/doctor.py`: 실데이터 표본을 정규화해 '정규화 필드 매핑' 항목으로 즉시 진단(미매핑 ❌ + FIELD_CANDIDATES 보강 안내). 실데이터 1순위 리스크(필드 불일치로 데이터가 조용히 비는 것)를 배포 시 바로 포착.
  - 테스트 tests/test_normalize_report.py(5종, 순수·오프라인 통과). skills/data-and-sources.md 문서화.
## v1.63 (2026-06-22)
- **문서 현행화(코드↔문서 동기화)**: 최근 ~20개 버전(시세 서버집계·생활권·바텀시트 통일·청약상세·푸시·모니터링·백업·임장·doctor)이 빠져 있던 내부 지침을 코드 현실에 맞춰 갱신. 코드 변경 없음.
  - skills/deploy-and-db.md: 마이그레이션 이력(0001~0011), 웹푸시·모니터링·백업·doctor 실제 패턴 추가.
  - skills/aggregations.md: price_overview(시세 서버집계)·생활권 점수(living) 규칙 추가.
  - skills/frontend.md: SheetShell 바텀시트/스와이프 통일·시세 드릴다운·상세 위젯·임장·푸시토글·데모폴백 보강.
  - skills/README.md: 레포 지도 현행화 + 원칙 7 '문서 동기화(필수)' 추가.
  - CLAUDE.md: §5 모델(PushSubscription·JobRun·Commute*)·§8 진행상태·§9 skills 색인(deploy/frontend/testing) 보강.
  - ROADMAP.md: 완료 항목 체크 + 'v1.50~v1.62 완료 로그' 추가(진행 SSOT 정합).
## v1.62 (2026-06-21)
- **배포 자가진단(scripts/doctor.py)**: 운영 PC에서 전체 스택을 한 번에 점검 — 설정·DB 연결·핵심 테이블(마이그레이션)·지역코드 실조회(MOLIT 1회)·데이터 신선도/건수·연동 키(카카오/지도/푸시/Sentry/경보)·백업 준비(pg_dump·쓰기권한)·관리자 토큰. 각 항목 ✅/⚠️/❌, ❌ 있으면 종료코드 1. 그동안 샌드박스에서 검증 불가했던 푸시·모니터링·백업·수집을 실서버에서 한 명령으로 확인. `--skip-live`로 외부호출 생략. monitoring.system_status·MolitClient·CHEONGJU_DISTRICTS 재사용. OPERATIONS.md 최상단에 사용 안내.
## v1.61 (2026-06-21)
- **임장 도우미(차별화)**: 관심 단지를 한 번에 둘러보는 '임장 코스 + 체크리스트'. 홈 '관심 단지'에 🧭 진입 버튼 → 바텀시트(TourSheet)에서 단지를 순번 코스로 나열, 단지별 임장 체크리스트(채광·소음·누수·주차·관리상태·동선 등 9항목)와 메모를 제공. 체크/메모는 기기에 저장(safeStore, 서버 전송 없음)되어 현장에서 그대로 확인 가능. 단지 탭 시 상세로 이동. 분석→실제 방문 전환(우리 약점)을 메우는 기능.
## v1.60 (2026-06-21)
- **백업 상태를 모니터링에 통합**: 백업/복구는 이미 구현돼 있음(scripts/backup.py·restore.py, 스케줄러 자동 백업 `SCHEDULER_RUN_BACKUP`, pg_dump/sqlite 분기, 보존정책, /admin/runs?name=backup). 이번엔 `system_status`가 **최근 백업 실패를 경고로 표시**하고 `ok` 판정에 반영하도록 보강 → `/admin/monitor`에서 수집뿐 아니라 백업 건강도까지 한눈에 확인.
- 정리: config의 백업 키 중복 정의 제거(backup_dir/backup_keep/scheduler_run_backup 단일화).
## v1.59 (2026-06-21)
- **관측성(모니터링) 설계·구현 — 무인 운영 대비**:
  - **실행 이력**: JobRun 모델 + 마이그레이션(0011_jobrun). 수집/지오코딩 등 배치의 성공·실패·소요·통계·오류를 기록.
  - **monitoring 서비스**: `record_job`(배치 감싸 기록+실패 시 경보), `alert`(ERROR 로그 + 웹훅 Slack/Discord), `system_status`(DB·데이터 신선도·최근 실행·카운트·연동여부·경고 통합), `recent_runs`.
  - **스케줄러 연결**: 수집·지오코딩을 record_job으로 감싸 자동 기록·경보(지오코딩 키 없음은 skip 처리).
  - **관리자 API/UI**: `GET /admin/monitor`(통합 상태), `GET /admin/runs`(실행 이력) — ADMIN_TOKEN 보호. /admin/ui에 '시스템 상태·실행 이력' 버튼 추가.
  - **에러 모니터링**: SENTRY_DSN 설정 시 Sentry 초기화(미설정·미설치 시 무동작). requirements에 sentry-sdk.
  - config: sentry_dsn·alert_webhook_url·data_stale_days. .env.example·OPERATIONS.md 문서화. 테스트 tests/test_monitoring.py.
  - 키 게이팅: 모든 경보/모니터링은 키 없어도 앱 정상 동작(로그만). 개인정보·키 값 미노출.
## v1.58 (2026-06-21)
- **웹푸시(푸시 알림) 구현 — 재방문 핵심**: 관심 단지 신고가·새 실거래를 휴대폰/브라우저 푸시로 발송(표준 웹푸시/VAPID, 유료 서비스 불필요).
  - 백엔드: PushSubscription 모델 + 마이그레이션(0010_push), services/push.py(pywebpush 지연 import·키 게이팅·만료 자동정리), API `/push/vapid|subscribe|unsubscribe|test`, notify_transactions에 발송 연결(알림 생성 시 해당 계정 구독으로 푸시; 실패해도 수집·알림 불영향). config VAPID 키 + push_enabled. scripts/gen_vapid.py 키 생성기. requirements에 pywebpush.
  - 프런트: 서비스워커(/sw.js, push·notificationclick), 구독/해지 헬퍼, 알림함 상단 '푸시 알림 켜기' 토글. 권한 요청·구독 저장·해지 일괄 처리.
  - 안전장치: VAPID 키 없으면 푸시만 비활성(앱·다른 기능 정상). HTTPS 필요. iOS는 홈 화면 추가(PWA) 후 동작. 테스트 tests/test_push.py(no-op 경로). 운영 절차는 OPERATIONS.md 참고.
## v1.57 (2026-06-21)
- **검색 → 하단 시트 통일**: 통합 검색을 전체화면 오버레이에서 공용 바텀시트(SheetShell)로 변경. 검색 입력창은 시트 헤더(핸들 아래 고정), 결과/검색홈은 본문 스크롤. 아래로 스와이프·배경 탭·취소로 닫힘 → 앱 전체 오버레이가 한 패턴으로 통일.
## v1.56 (2026-06-21)
- **청약 상세 추가(마감 포함 열람)**: 청약/분양 카드를 탭하면 상세 시트(SubDetail/SubSheet)가 열림 — 지역·청약기간·총공급·분양가·경쟁률·최저가점, 주택형별(세대·분양가·경쟁률·최저/평균가점), 청약홈 바로가기, 출처 고지. **마감된 공고도 결과·기록 참고용으로 열람 가능**(상단에 마감 안내). 카드에 › 표시 + 탭 가능.
- **상세 화면 뒤로가기 버튼 제거**: 시트로 전환된 상세(단지·매물·게시판)에서 상단 '뒤로(‹)' 버튼 삭제 — 시트는 핸들·아래로 스와이프·배경 탭으로 닫음(중복 제거). 전체화면 폼(매물 등록)·작성자 보기의 뒤로 버튼은 유지.
## v1.55 (2026-06-21)
- **게시판 상세 → 바텀시트 통일**: 커뮤니티(게시판) 글 상세도 전체화면 전환에서 바텀시트(PostSheet)로 변경. 리스트 유지·맥락 보존. 글 편집/작성자 보기는 기존 전체화면 흐름 유지.
- **시트 공용화(SheetShell) + 아래로 스와이프 닫기**: 단지·매물·게시판·통근·예산 5개 시트의 중복 마크업을 공용 `SheetShell`로 통합(유지보수·일관성). 스크롤이 맨 위일 때 **아래로 끌어내리면(터치 스와이프) 시트가 닫힘**(110px 이상 시 닫기, 미만이면 스르륵 복귀). 내부 스크롤·버튼과 충돌하지 않도록 '맨 위에서 아래로'일 때만 드래그 인식. 기존 배경 탭·핸들·× 닫기 그대로.
## v1.54 (2026-06-21)
- **매물 상세 → 바텀시트 통일**: 매물 게시판의 상세화면을 전체화면 전환에서 단지·통근·예산과 동일한 **바텀시트(ListingSheet, 93vh·드래그핸들·dim 배경)**로 변경. 리스트가 유지된 채 위로 시트가 떠 맥락 유지·뒤로가기 일관성 확보. 상단 BackBtn·핸들·배경 탭으로 닫힘. 외부 딥링크(openId)·카드 탭 모두 시트로 표시.
## v1.53 (2026-06-21)
- **시세 조건 변경 반응속도 개선**: 백엔드 미연결(demo) 상태에선 /price/overview 요청을 건너뛰고 즉시 demoOverview를 사용 → 구·유형·평형을 바꿀 때마다 요청 실패를 기다리던 지연 제거(미리보기 체감 개선). 실서버(live)에선 정상 요청하되 4초 안전 타임아웃(AbortController)으로 행 걸림 방지 후 폴백. 로딩 중에는 직전 결과를 유지하고 '불러오는 중…' 표시(빈 화면 깜빡임 없음).
## v1.52 (2026-06-21)
- **버그픽스(시세 탭 빈 화면)**: 시세 탭의 /price/overview 폴백에서 catch 가드가 `if(on)return`으로 뒤집혀 있어, 백엔드 미연결(미리보기/네트워크 실패) 시 demoOverview 폴백이 깔리지 않고 데이터가 비어 보이던 문제 수정(`if(!on)return`). 실서버 정상 응답 시 빈 결과는 그대로 '거래 0건' 안내로 노출(왜곡 없음).
## v1.51 (2026-06-21)
- **생활권 점수(차별화)**: 단지 상세에 반경 1.5km 내 인프라 접근성을 투명하게 점수화한 '생활권 점수' 추가. 교통(지하철)·편의(마트)·학교·의료(병원) 4개 카테고리의 **최단 거리 기반**(300m 이내 100점, 1.5km 40점 선형, 반경 내 없으면 0점) 가중 평균(0~100)+등급(최상/좋음/보통/아쉬움). 카테고리별 점수·최단거리·개수를 함께 표시해 '왜 이 점수인지' 공개(블랙박스 아님). 실거주 만족도와 다를 수 있는 거리 기준 참고치임을 고지(출처: 카카오 장소).
  - 백엔드: services/living.py(`living_score(poi)`), /complex/detail 응답에 living_score 포함(좌표+카카오 키 있을 때, 없으면 None). 프런트: LivingScore 카드(인근 인프라 위). 데모는 표본 배지.
  - 테스트 tests/test_living.py(순수 로직 3종). 실서버에선 카카오 키+지오코딩 좌표가 있어야 실제 점수가 계산됨.
## v1.50 (2026-06-21)
- **시세 집계 서버 이전(확장성)**: 시세 탭이 거래 500건을 클라이언트로 받아 집계하던 구조를 **서버 집계 API `GET /price/overview`**(stats.price_overview, 캐시 적용)로 대체. 구/유형/평형대를 넘기면 윈도우(최근 N개월) 전체 실거래로 구 요약(중앙 매매·전세가율·거래량·전월 등락)과 단지 리스트를 집계해 반환 → 데이터·지역 확장 시에도 표본 왜곡·페이로드 폭증 없음. 프런트는 이 API 사용(검색·정렬은 구 단위 소목록에서 클라이언트 처리), 무네트워크 시 demoOverview 폴백.
  - 검증은 실서버에서 `GET /price/overview?lawd_cd=43113&property_type=apartment` 및 pytest 권장(샌드박스는 DB 불가). demoOverview는 node로 동등성 확인.
## v1.49 (2026-06-21)
- **시세 탭 전면 개편 — ‘지역 → 단지’ 드릴다운**(군더더기 제거). 기존 3서브탭(리스트·지도·랭킹)+필터 6종 → 핵심 흐름으로 정리:
  - 상단 **구 칩**(전체·상당·서원·흥덕·청원) → 선택 구 **요약 카드**(평균 매매 중앙값·전월 등락·전세가율·거래량, tx에서 직접 계산해 표시와 일치) → **단지 리스트**(거래 많은 순 기본, 단지명·대표 시세·거래수, 탭 시 상세 시트).
  - 평형·유형·정렬 등 **세부 필터는 ‘상세’로 접어** 기본 비노출. 검색은 한 줄.
  - 서브탭은 **리스트/지도 2개로 축소, 랭킹 제거**(홈과 중복). 지도=기존 HeatTab 유지.
  - 참고용·신고 지연 고지 유지(왜곡 없음). (구 Price/Rank 컴포넌트는 미사용으로 잔존 — 추후 정리)
## v1.48 (2026-06-21)
- **신고가 경신 알림(신규)** — 재방문 엔진 강화. 기존 ‘관심 단지 신규 실거래 N건’ 알림(이미 구현됨)에 더해, 수집된 신규 매매가가 그 단지의 ‘직전까지 최고가’를 넘으면 `type=new_high` 알림 생성(단지당 1건은 신고가 메시지로 격상). 메시지는 사실만: 신고가·직전 최고가(억). 커서 기반 멱등 유지, 로그인 사용자·실거래(비표본·비해제)만. 프런트 알림함이 new_high를 📈 아이콘으로 표시하고 탭하면 단지로 이동.
  - 동작 검증은 실서버에서 `python -m pytest` + 수집 파이프라인(collect) 후 확인 필요(샌드박스는 DB/네트워크 불가).
## v1.47 (2026-06-21)
- **‘이 단지 매물 보러가기’(외부 연결)**: 단지 상세에 외부 매물 검색 링크 추가(네이버 통합검색·네이버 지도, 단지명+구로 검색). 우리 약점인 ‘실제 매물·마지막 한 걸음’을 운영 부담 없이 보완. 딥링크는 단지 내부ID가 필요해 이름만으론 부정확 → 항상 동작하는 검색 URL 사용. ‘외부 사이트·중개/광고 무관’ 고지 포함(객관성·비제휴).
## v1.46 (2026-06-21)
- **거래 동향 배지(신규)**: 단지 상세 면적별 섹션 앞에 ‘거래 활발/보통/한산’ 표시. 최근 3개월 매매 신고 건수를 직전 3개월과 비교(활발=늘고 1.3배↑·한산=0.7배↓)해, 가격만으로 알기 어려운 ‘거래를 동반한 변화’를 참고로 제공. 색은 가격 방향(빨강/파랑)과 구분되게 TEAL/회색 사용. 표본 적으면 미표시·참고용 고지.
## v1.45 (2026-06-21)
- **적정가 체크(신규)**: 면적별 섹션에 매물·호가를 입력하면 그 평형의 최근 실거래 분포에서 위치를 진단. 중앙값 대비 %, 저점~중앙~고점 범위 막대 + 입력가 마커, ‘최근 N건 중 이 가격보다 낮은 거래 K건(하위 P%)’, 저렴/시세/비싼 판정과 신고가·급매 주의. 백엔드 면적 객체에 거래 분포 `amounts` 노출(공개 실거래값). 참고용·표본 적음 고지 포함(왜곡 없음).
## v1.44 (2026-06-21)
- **내 예산 맞춤 추천도 바닥 시트로 표출**. 홈에는 진입 카드(💰)만 두고, 누르면 `BudgetSheet`(93vh)에 입력·필터·추천 결과를 전부 인라인으로 표출. 기존 ‘N곳 보기→중첩 시트’ 제거(시트 안에서 바로 목록). 상세·통근·예산 모두 동일 시트 패턴으로 통일. `BudgetPicks`에 `embedded` 옵션 추가(제목 중복 제거).
## v1.43 (2026-06-21)
- **통근권도 바닥 시트로 표출**. 전체화면 통근 화면을 없애고 `CommuteSheet`(93vh 바닥 시트)에 통근 검색·결과·지도를 그대로 담음. 결과 탭 → 통근분 요약 시트 → ‘상세 보기’ 시 단지 상세 시트로 연결(상세 시트가 위에 표시). 상세·통근 모두 동일한 시트 패턴으로 통일.
## v1.42 (2026-06-21)
- **단지 상세를 바닥 시트에 전체 표출**(요약→상세 분리 제거). 별도 전체화면 상세 페이지를 없애고, 단지를 누르면 `DetailSheet`(93vh 바닥 시트)에 상세 내용 전부를 그대로 펼침. 시트 안에서 다른 단지를 누르면 같은 시트가 그 단지로 갱신(스크롤 상단으로 리셋).
- 요약 전용 시트(ComplexQuickSheet) 단계 폐지. 통근 결과는 통근분 요약 시트 → ‘상세 보기’ 시 동일 상세 시트로 연결.
## v1.41 (2026-06-21)
- **모든 단지 탭 → 공통 요약 시트로 통일**. 전역 `ComplexQuickSheet` 신설: 단지를 누르면 어디서든(홈 목록·검색결과·순위·급상승/대장·최고상승하락·관심/최근·예산추천) 동일한 바닥 시트로 **대표 시세·전세가율·거래건수·실거래 범위** 요약을 보여주고, ‘전체 상세 페이지 보기 →’로 이동.
  - `openComplex`(요약 시트) / `openDetail`(전체 상세) 분리. 상세 화면 내부 이동·통근 결과는 상세로 직행(통근은 통근분 포함 자체 요약 시트 유지).
## v1.40 (2026-06-21)
- **바닥 시트(팝업) 패턴으로 리스트 표출 통일**(레퍼런스 ‘지금인기/순위’ 방식).
  - 공통 `Sheet` 컴포넌트 신설(딤 배경·480px 중앙·드래그 핸들·헤더·스크롤, body 포털). `RankSheet`가 이를 재사용.
  - **내 예산 맞춤 추천**: 인라인 긴 목록 → ‘추천 단지 N곳 보기 ›’ 버튼 → 시트로 표출. 필터(유형·지역)는 카드에 유지.
  - **통근권 결과 클릭**: 곧장 상세로 가지 않고 **요약 시트**(통근 분·시세·지역·유형 + ‘단지 상세 보기 →’)로 표출.
## v1.39 (2026-06-21)
- **홈 카드 간격 정리**: 커스텀 카드(예산 추천·최고 상승하락·통근 CTA)가 marginTop 2px라 Collapsible(12px)과 간격이 들쭉날쭉하던 문제 → **12px로 통일**.
## v1.38 (2026-06-21)
- **최고 상승·하락: 정렬 추가** — 변동률(%)/변동액(억·만) 토글. 싼 소형 단지의 % 과장 왜곡을 변동액 정렬로 보완.
- **전체화면 오버레이 중앙 정렬 고정** — 검색 화면·순위 시트·약관 모달을 480px 모바일 폭으로 가운데 정렬(넓은 화면에서 풀폭으로 퍼지던 문제 해결).
- **홈 추천 통합** — 별도 '맞춤 추천(관심 지역 기반)' 제거하고, **'내 예산 맞춤 추천'에 지역 필터**(전체/★관심지역/상당·서원·흥덕·청원) 추가. 예산·유형·지역을 한 곳에서. 백엔드 `affordable_complexes`에 `lawd_cds`(구 필터) 추가.
## v1.37 (2026-06-21)
- **홈 ‘구별 매매 추이’ 그래프 제거** → 그 자리에 **‘최고 상승·하락 아파트’** 추가.
  - `stats.top_movers`: 같은 단지·평형에서 **직전 거래 대비** 실거래가가 가장 많이 오른/내린 순위(최근 2건 비교). board에 `top_movers` 포함.
  - 프런트 `TopMovers`: 상승/하락 토글 + 순위 + 단지·평 + 지역 + 변동액(±, 억/만)·변동률(%) + 이전가›현재가. 집계기준 ⓘ(직전 거래 비교·참고용·이상치 가능) 표기. 금액 포맷 `manKor`(억/만, 부호) 추가. 데모 반영.
## v1.36 (2026-06-21)
- **레이아웃 폭 고정(모바일)**: 콘텐츠 컨테이너 `max-width` 1040px(데스크톱) → **480px(모바일, 가운데 정렬)**. 넓은 화면에서 UI가 늘어났다 줄었다 하던 문제 해소 — 폰·모바일웹·데스크톱에서 동일한 폭으로 표시. (하단 네비도 동일 폭)
## v1.35 (2026-06-21)
- **헤더 검색창 축소**: 풀폭 → 우측 정렬 약 200px(절반 이하)로 줄이고 안내문구 간소화('단지·지역 검색').
- **버그 수정: 거래 급상승/대장 배너 클릭 시 순위 시트가 카드 안에 갇혀 잘리던 문제**. 시트를 `ReactDOM.createPortal`로 body에 렌더해 화면 하단 시트로 정상 노출(카드 `overflow:hidden`/transform 영향 제거).
## v1.34 (2026-06-21)
- **헤더 개편 + 검색 화면 강화**(레퍼런스 반영).
  - 헤더에 **작은 검색 pill**을 올림(모든 탭 공통). 누르면 전체 검색 화면(SearchOverlay)이 뜸. 본문에 있던 큰 인라인 검색창 제거.
  - 검색 화면 빈 상태에 **최근 본 단지** + **인기 순위(단지=🔥거래 급상승 / 지역=구별 평단가)** 추가. 메달(🥇🥈🥉)·지역·집계기준 ⓘ 표기(왜곡 없음).
  - **평수(평/㎡)·다크모드·새로고침·계정**을 헤더 **☰ 설정 메뉴**로 통합 → 헤더 간결화. (평수·다크모드 위치 추천 반영)
## v1.33 (2026-06-21)
- **랭킹 배너 → 바닥 시트(모달)로 전환**. 거래 급상승·대장 아파트 배너를 누르면 인라인으로 펼쳐 아래를 밀어내지 않고, **하단에서 올라오는 시트**(딤 배경)로 전체 순위를 보여줌(레퍼런스 UX 반영).
  - 시트: 🥇🥈🥉 메달(1~3위) + 순위 + 단지명 + 지역(시·구·동) + 지표(▲거래건수/대표가). 헤더에 ‘집계기준 ⓘ’로 산정 방식 설명(왜곡 없음). 항목 탭 → 단지 상세.
  - 거래 급상승 결과에 동(dong) 추가로 지역 표기 강화.
## v1.32 (2026-06-21)
- **홈 상단 롤링 배너 2종 추가**(경쟁 앱 '인기 급상승' 형태 차용, 정직한 신호로 구현).
  - **🔥 거래 급상승**: 최근 90일 거래량이 직전 90일 대비 늘어난 단지(`stats.trending_complexes`). 조회수·관심수 같은 미검증 사용자 데이터는 쓰지 않고 ▲N건으로 표기(왜곡 없음). 급상승 표본 부족 시 '거래 활발'(최근 거래량 순)로 폴백.
  - **👑 대장 아파트**: 기존 대표가 중앙값 TOP을 같은 배너 형태로. (기존 큰 카드형 LandmarkCarousel은 제거하고 배너로 통합)
  - 공통 `TickerBanner`: 자동 롤링(3.5s) + 탭하면 전체 순위 펼침, 항목 탭 → 단지 상세. 백엔드 board에 `trending` 포함, 데모도 반영.
## v1.31 (2026-06-21)
- **신규: 홈 ‘내 예산 맞춤 추천’(자본별 매물 추천)** — 대출 계산에서 분리한 독립 커스텀 기능.
  - 홈 상단에 배치. 보유 현금(필수)·연소득(선택, 동의 시) 입력 → **이 기기에만 저장(서버 전송·저장 없음)**, 다음 방문부터 자동 활용.
  - 예산(자기자본+대출) 산출 → 그 이하 단지를 ‘자기자본+대출·월상환·시세’와 함께 추천. **전 유형(아파트·오피스텔·빌라·단독) 기본 + 유형 필터**. 표본 적음·비아파트 개략 라벨로 왜곡 방지.
  - 백엔드 `affordable_complexes`: 전 유형 지원(`property_type='all'`/None) + 결과에 `property_type` 포함.
  - 기존 대출 상세의 ‘이 예산으로 살 수 있는 단지’ 블록은 제거(중복 해소). 단지별 적정성은 상세의 ‘실구매력 진단’이 계속 담당.
## v1.30 (2026-06-21)
- **시세 탭 검색바 중복 정리**. 상단 전역 검색바를 시세 탭에서는 숨김(홈·청약·매물·게시판엔 유지). 시세 탭은 유형·구·평형·정렬과 묶인 자체 목록 검색 하나만 노출 → 탭당 검색창 1개로 깔끔.
## v1.29 (2026-06-21)
- **통근권 지도 뷰 추가**. 통근 검색 화면에 리스트/지도 토글.
  - 지도: **목적지 마커(🏢)** + 결과 단지 마커(통근 분 표시, 시간대별 색: ≤15 초록·≤30 청록·≤45 주황·45+ 빨강). 핀 클릭 → 하단 시트(단지명·구·유형·분·시세 + ‘단지 상세 →’). 결과 범위에 맞춰 자동 fitBounds.
  - 백엔드 `commute` 응답에 목적지/단지 좌표(lat/lng) 노출, 데모 결과에도 좌표 포함(미리보기 동작). 좌표 없으면 안내(왜곡 없음).
## v1.28 (2026-06-21)
- **차별화 ③ 적정가/실구매력 진단**. 대출 계산에 ‘이 단지가 내 예산에 적정/빠듯/무리’ 판정 추가(매수 의사결정 도움).
  - 백엔드 `loan._affordability`: 필요 대출이 LTV·DSR 한도 안인지 + 월 상환액의 소득 대비 **부담률**로 4단계 판정(적정 ≤25% · 빠듯 25~35% · 부담 큼 35%↑ · 무리=한도초과/현금부족). `estimate` 반환에 `affordability` 포함.
  - 프런트 `AffordVerdict` 카드: 판정 배지 + 월 예상 상환 + 부담률(+필요대출), 상황별 코멘트(한도 부족/현금 부족/부담률). 데모 `loanLocal`도 동일 로직 반영.
  - 기존 대출 동의(ConsentGate)·미저장(stateless) 흐름 재사용 — 민감정보(소득) 입력은 맞춤 모드에서만, 저장 안 함(9.A 준수).
## v1.27 (2026-06-21)
- **차별화 ② 통근권 — 프런트 + 검색 화면**. 홈에 ‘🧭 통근권으로 집 찾기’ 진입 카드 → 전용 검색 화면.
  - 목적지 선택(교통/직장/공공/교육 칩) → 수단(자동차/대중교통) → 유형 → ‘N분 이내’ 슬라이더 → **시간순 단지 리스트**(분 배지 + 구·유형 + 최근 중앙 매매가, 추정/실측 라벨). 단지 탭 → 시세 상세.
  - 백엔드 `search_by_commute`에 결과별 `lawd_cd`·`price`(최근 N개월 중앙 매매가) 결합 → ‘시간 + 가격’ 동시 판단.
  - 데모: 청주 4개 목적지 + 단지 좌표로 즉석 haversine 추정(미리보기 동작). ‘추정(직선거리)’ 라벨로 왜곡 없이 표기.
## v1.26 (2026-06-21)
- **차별화 ② 통근권 — 데이터/백엔드 토대**(설계 우선, 운영·확장 고려). 프런트는 후속.
  - 모델: `CommuteDestination`(운영자 관리 목적지) + `CommuteTime`((단지×목적지×수단) 통근시간 캐시, 'N분 이내' 인덱스). 마이그레이션 `0009_commute`(create_table·inspect 가드·portable).
  - 서비스 `services/commute.py`: 카카오모빌리티 길찾기 실측(`api`) 또는 직선거리 추정(`haversine`) — 정확도 라벨로 구분(왜곡 없음). 캐시 우선 + 콜드스타트 즉석 추정.
  - 시드 `app/data/commute_seed.py`(청주 8개 거점: 오송역/오송바이오/오창산단/시청/도청/공항/터미널/충북대, 좌표 seed_approx). 스크립트 `scripts/seed_commute.py`(+--geocode), `scripts/compute_commute.py`(증분 배치).
  - API: `GET /commute/destinations`, `GET /commute/search?dest_id=&mode=&max_minutes=&property_type=`. 설정값(평균속도·우회계수·TTL) 분리.
  - DATA.md/OPERATIONS.md 운영 절차 + `tests/test_commute.py`.
## v1.25 (2026-06-21)
- **단지 상세: ‘전세 안전도’ 섹션을 대출 계산 바로 아래로 이동**. 매매 상세의 매수자 흐름(가격 → 면적별 상세 → 대출 계산 → 전세 안전도)에 맞게 재배치. 상단은 가격·신뢰 정보에 집중.
## v1.24 (2026-06-21)
- **차별화 ① 실거래 신뢰 필터** (시세 왜곡 줄이기 — ‘왜곡 없음’ 강화). 다른 부동산 앱이 약한 지점.
  - 데이터층: `transactions.trade_method`(거래유형 중개/직거래) 컬럼 추가 + MOLIT `dealingGbn/거래유형` 파싱(`agent`/`direct`/null). 마이그레이션 `0008_tx_trade_method`(nullable·inspect 가드·portable). 정정 경로에서도 trade_method 갱신.
  - 통계층: `complex_detail`/`_area_block`이 거래행마다 **정정(corrected)·직거래(direct)·이상치(outlier)** 플래그 제공(이상치=같은 평형 중앙 평단가 대비 ±30% 초과, `stats._tx_out`). 단지·평형 **표본 신뢰도**(`reliability`: low/fair/ok), **해제 건수**(`canceled_count`) 노출.
  - 프런트: 최근 실거래 행에 정정/직거래/이상치 배지(이상치는 취소선). ‘표본 적음’ 표시. 단지 상단에 ‘해제 N건 제외 · 표본 적음’ 안내(callout).
  - 데모/문서/테스트: demoDetail에 4개 신호 반영(미리보기 시연), DATA.md 운영 메모, `tests/test_trust.py` 추가. 시세 리스트도 해제분 제외.
## v1.23 (2026-06-20)
- **공유용 시세 카드 (바이럴 성장 기능)**. 단지 상세 하단 ‘📤 이 시세 카드 공유하기’ 버튼 → 단지 시세를 예쁜 카드 이미지로 생성.
  - 외부 라이브러리 없이 **Canvas 2D로 직접 렌더**(오프라인 동작): 단지명·구/동/유형/연식, 최근 매매가+전고점 대비, 중앙값·평단가·거래건수, 전세 안전도 게이지, 최근 N개월 추이 미니차트, 출처/참고용 고지.
  - **이미지 저장**(PNG 다운로드) + **공유하기**(Web Share API — 카톡 등 네이티브 공유 시트; 미지원 환경은 저장 후 첨부 안내).
  - 평형을 좁혀 본 경우 그 평형 기준, 전체 보기면 단지 전체 기준 카드. 모의 데이터는 ‘모의’ 배지 표기(왜곡 방지).
  - 참고: 아티팩트 미리보기 iframe에선 저장/공유가 제한될 수 있고, 실제 배포 앱·모바일에서 정상 동작.
## v1.22 (2026-06-20)
- **단지 상세: ‘전세 안전도(깡통전세 위험)’ 진단 섹션 추가**. 기존 전세가율 데이터 기반(새 API 없음, 왜곡 없음).
  - 4단계 게이지: ~70% 안전한 편 · 70~80% 보통 · 80~90% 주의 · 90%~ 위험(깡통 우려). 현재 전세가율 위치 마커 표시.
  - 단계별 코멘트 + ‘계약 전 확인’ 체크리스트(선순위 채권·근저당, 임대인 세금 체납, 반환보증 가입, 확정일자·전입신고).
  - 보증금 반환보증 안내: HUG(khug.or.kr)·HF(hf.go.kr)·SGI. ‘참고 지표일 뿐, 법률·금융 자문 아님’ 고지 포함.
  - 평형을 좁혀 본 경우 해당 평형 전세가율 기준, 전체 보기일 땐 단지 전체 기준으로 표기.
## v1.21 (2026-06-20)
- **단지 상세: 클릭한 평형만 표시**. 리스트/그룹에서 특정 거래(특정 전용면적)를 누르면, 그 단지의 '같은 평형'만 보이도록 변경(이전엔 단지의 모든 평형이 함께 표출).
  - 클릭 시 `exclusive_area`를 상세로 전달(`sel.area`). 상세에서 전용면적을 평(3.3㎡)으로 반올림해 같은 평형대만 필터(예: 84.9㎡·85㎡ → 둘 다 26평이라 함께, 101.2㎡(31평)는 분리).
  - 좁혀진 경우 상단에 '전용 OO㎡ 평형만 보는 중 · [전체 평형 보기]' 배너 노출. 버튼으로 전 평형 보기로 전환.
  - 대출 계산의 면적 토글·자동입력도 해당 평형 기준으로 한정. 평형 전환 시 대출 선택 초기화.
  - 면적 정보가 없는 진입(검색·관심·최근·대장아파트·지도 핀·'단지 상세 보기')은 기존대로 전체 평형 표시.
## v1.20 (2026-06-20)
- **버그 수정: 단지 상세가 안 뜨던 문제(데모/standalone 화면)**. 데모 폴백 함수 `demoDetail`이 정의되지 않은 변수(`trough`·`amts`·`pmed`·`jrate`·`fb`·`recent`)를 참조해 런타임 오류로 throw → Detail이 스켈레톤(로딩) 상태에서 멈춰 상세가 표시되지 않았음. 누락 변수를 백엔드와 동일한 의미(저점·중앙값·전세가율·최근거래 등)로 정의해 해결. (실서버 경로는 영향 없었음 — 데모 전용 버그)
- node로 demoDetail 회귀 검증 추가 확인(found/median/jeonse_ratio/recent 정상).
## v1.19 (2026-06-20)
- **홈 ‘내 동네’ 삭제**: 홈 상단 구 선택 칩 제거(맞춤 추천은 관심 지역 기반으로 유지).
- **시세 ‘조건 저장’ 삭제**: 저장된 조건 칩 + ‘＋ 이 조건 저장’ 버튼 제거.
- **시세 조건 UI 전면 개편**: 흩어져 있던 조건(유형·구·검색·평형·정렬)을 리스트 상단 **한 장의 카드**로 통합·정돈.
  - 구성: ① 검색창 → ② 유형·구 드롭다운(2열) → ③ 평형 세그먼트 → ④ 정렬 세그먼트 → ⑤ 총 건수 · 관심만 · 초기화.
  - 칩 난립 대신 라벨+세그먼트 컨트롤로 한눈에 보이게. 활성 필터가 있으면 ‘초기화’ 노출.
  - 지도·랭킹 뷰는 유형만 필요하므로 상단에 유형 셀렉터만 간결하게.
## v1.18 (2026-06-20)
시세 탭 UX 6종 (인기 부동산 앱 패턴 반영):
- **① 단지·동 인라인 검색**: 리스트 상단에 검색창. 단지명/법정동 부분일치로 즉시 필터.
- **② 평형(면적) 필터**: 전체/소형(~60㎡)/중형(60~85)/대형(85~) 칩.
- **③ 단지 묶음 카드**: 개별 거래 나열 → 단지별로 묶어 대표가(중앙값)·건수·평단가 표시, 탭하면 개별 거래 펼침 + ‘단지 상세 보기’. (단독·다가구는 개별 행 유지)
- **④ 평단가순 정렬**: 가격순/평단가순/최신순. 정렬값이 단지 그룹 순서까지 반영.
- **⑤ 지도 핀 → 하단 시트**: 단지 핀 클릭 시 화면 전환 대신 지도 위 하단 카드로 대표 평단가·건수 미리보기 + 상세 이동. (구 핀은 기존대로 구 드릴다운)
- **⑥ 관심만 보기**: 관심 등록 단지가 있으면 ‘★ 관심만’ 토글로 리스트를 관심 단지로 한정.
- favs를 App→PriceHub→Price로 전달. 거래행 마크업을 TxRow 컴포넌트로 분리(재사용).
## v1.17 (2026-06-20)
- **시세 탭: 유형 + 구 필터를 상단에 함께**: 그동안 유형은 상단 공유 바, 구는 리스트 내부에 떨어져 있던 것을 합침. 리스트 뷰에서 상단 바에 [유형][구]가 나란히 노출되어 한 번에 조건 설정. (지도·랭킹 뷰에선 구 필터 숨김 — 전체 개요라서)
- **소식 탭 제거 → 홈 '오늘의 정보'로 통합**: 하단 탭을 6→5개(홈·시세·청약·매물·게시판)로 축소. 부동산 뉴스·정책·지원 목록을 홈 '오늘의 정보' 영역(청약 임박 + 뉴스 + 정책 collapsible)으로 이동. 정책은 기본 접힘.
## v1.16 (2026-06-20)
- **홈 '구별 매매가 랭킹' 섹션 삭제**(시세 탭 랭킹과 중복). 관련 미사용 변수(gus/maxpp/sortMine) 정리.
- **대장아파트 클릭 시 상세가 비던 문제 보강**: `complex_detail`이 유형(property_type) 힌트로 0건이면 유형을 무시하고 `name+lawd_cd`로 재조회하도록 폴백 추가(잘못된 유형 힌트에도 단지를 찾음). 캐러셀 클릭 시 gu·dong도 함께 전달.
## v1.15 (2026-06-20)
- **홈 '오늘의 정보' 위젯 추가(실용 정보)**: 홈 하단에 ① 청약 임박(접수중>접수예정 우선 1건, 상태 배지·기간·위치, 탭 시 청약 탭) ② 최신 뉴스 1건(출처·일자, 링크/뉴스 탭) + '청약 전체'·'뉴스·정책' 바로가기. 청약은 /subscription 직접 조회(실패 시 예시 폴백), 뉴스는 기존 feed 재사용. 앞서 제안한 홈 5블록 구성 완성.
## v1.14 (2026-06-20)
- **홈 '대장아파트' → 자동 슬라이드 배너(캐러셀)**: 평형(소·중·대형) 구분을 없애고 단지 대표가 중앙값 기준 **TOP 5**만 노출. 3.5초마다 자동 전환, 마우스오버·터치 시 일시정지, 하단 점(dots)으로 이동, 카드 탭 시 단지 상세. 백엔드가 이미 내려주던 평면 `landmark`(top5) 사용.
## v1.13 (2026-06-20)
- **시세 탭 통합 — 유형(매물종류)을 전 뷰 공통 컨트롤로 승격**: 그동안 리스트/지도/랭킹이 각자 유형 셀렉터를 따로 가져 뷰 전환 시 맥락이 끊겼음. PriceHub 상단에 공유 '유형' 컨트롤을 두고 리스트·지도·랭킹에 모두 반영(유형 변경 시 랭킹 데이터도 자동 재요청). '전체 유형'은 리스트에서 지원, 지도·랭킹은 아파트 기준으로 안내 표기.
  - 전략: 시세 탭 = '쌓기'가 아니라 '상단 컨트롤(유형 공유) → 뷰 토글(한 번에 하나) → 구·동·단지 드릴다운'의 탐색 도구. 길이 증가 없이 일관성 확보.
  - 각 뷰 고유 컨트롤은 유지: 리스트(구·정렬·거래유형), 지도(구/단지 단위), 랭킹(지표).

## v1.12 (2026-06-20)
- **홈 화면 재구성(간결화 + 핵심 보완)**:
  - **추가**: 최상단에 '청주 아파트 시세 요약 히어로'(평균 매매/전세 + 전월·전년 등락 + 기준월). 그동안 백엔드 city_summary 가 계산되지만 홈에 미표시였던 핵심 누락을 보완. `/dashboard/board` 응답에 `city` 추가.
  - **정리(중복 제거)**: 시세 탭과 겹치던 '구별 최신 실거래' 섹션 제거, '구별 매매 추이'는 기본 접힘, '구별 매매가 랭킹' 하단에 '시세에서 더보기(지도·최신 실거래)' 버튼 추가 → 전체 탐색은 시세 탭으로 유도.
  - 결과: 펼친 섹션 8개 → (히어로 + 관심/최근/내 동네 + 맞춤추천 + 대장 + 랭킹) 중심으로 축약. 개인화·정직성 배지 유지.
  - 오프라인 데모(demoBoard)에도 city 샘플 추가.

## v1.11 (2026-06-20)
- **집계 기본 윈도우 = 최근 12개월** (`.env` `aggregate_months`, 기본 12). 현재 시세(중앙값·평단가·전세가율·거래량·랭킹·지도·비교·예산매칭)는 최근 12개월 실거래만 사용.
  - `stats._load`(최근 N개월) / `_load_all`(전체) 분리. 전년대비(YoY)·단지 다년 추이만 `_load_all`.
  - 단지 상세 '고점/저점 대비'도 최근 N개월 기준으로 라벨 정정.
  - **화면 표기**: /config 의 `aggregate_months` → 프런트 `AGG_MONTHS`. 푸터·단지상세·비교·예산매칭에 "최근 N개월 실거래 기준" 노출.
  - 테스트 test_stats.test_aggregate_window_excludes_old. DATA.md·aggregations 스킬 갱신.
- 참고: 중앙값(median)은 의도적 선택 — 실거래가의 이상치(고가·증여성 저가)에 강건해 대표 시세로 평균보다 적합.

## v1.10 (2026-06-20)
- **운영자용 데이터 설명서 추가(DATA.md)**: 저장 환경, 공통 규칙(만원 단위·is_sample·is_canceled·source·raw_payload), 핵심 테이블(regions/complexes/transactions) 컬럼 상세, 매물·커뮤니티·개인화 테이블 요약, 데이터 흐름(수집→정규화→적재→집계), 집계 기간 기준, 보존·파기, 개인정보, **PostgreSQL 테이블·데이터 확인 방법(psql/pgAdmin/SQL 예시)** 정리. README·OPERATIONS 에서 링크.

## v1.9 (2026-06-20)
- **버그픽스(PostgreSQL 마이그레이션 이식성)**: SQLite 기준으로 작성돼 PG 에서 깨지던 부분 수정. 전 마이그레이션·스키마 경로 전수 점검.
  - `migrations/0003_tx_cancel`: `UPDATE ... is_canceled = 0` → `= false`(PG 는 boolean 에 정수 미허용). **이번 에러의 직접 원인.**
  - `db/session.init_db`: PostgreSQL 에서는 `create_all`/`_ensure_columns` 를 호출하지 않음 → 스키마는 Alembic 단일 권위. (create_all↔migration 충돌·raw DDL 위험 제거)
  - `db/session._ensure_columns`: 비-SQLite 에서 즉시 반환(raw DDL `DATETIME`·`=0` 는 SQLite 전용).
  - 점검 결과: 나머지 마이그레이션(0001·0002 baseline create_all·0003_alerts·0004·0005·0006·0007)은 모두 `inspect` 가드로 멱등·이식성 OK. 앱 쿼리는 ORM 이라 dialect 안전.

## v1.8 (2026-06-20)
- **버그픽스(마이그레이션 DB URL의 % 문자)**: 비밀번호에 `@`(=`%40`)·`%` 가 들어간 `DATABASE_URL` 을 alembic 이 ConfigParser 에 넣다가 `invalid interpolation syntax` 로 죽던 문제 수정.
  - `migrations/env.py`: DB URL 을 ConfigParser 를 거치지 않고 설정에서 직접 읽어 `create_engine` 으로 사용(`%/@` 인코딩 안전, SQLAlchemy 가 정확히 디코딩).
  - `scripts/db_upgrade.py`: `sqlalchemy.url` 을 더 이상 cfg 에 주입하지 않음(미사용 import 정리).

## v1.7 (2026-06-19)
- **버그픽스(Windows 마이그레이션)**: `python/uv -m scripts.db_upgrade` 실행 시 한글 Windows 로케일(cp949)에서 `alembic.ini`의 한글 주석을 못 읽어 `UnicodeDecodeError`가 나던 문제 수정.
  - `alembic.ini`를 ASCII로 정리(주석 영문화).
  - `scripts/db_upgrade.py`가 `alembic.ini`를 직접 읽지 않고 `Config()`를 코드로 구성(script_location·sqlalchemy.url 주입) → 로케일/인코딩과 무관하게 동작.

## v1.6 (2026-06-19)
- **네비 정리(8→6탭)**: '가격을 본다'가 흩어져 있던 시세·랭킹·지도를 **하나의 '시세' 탭**으로 통합(상단 리스트/지도/랭킹 토글). 하단 네비는 홈·시세·청약·매물·게시판·소식 6개로 단순화.
  - PriceHub 래퍼(뷰 토글) + priceView 상태. 기존 Price/HeatTab/Rank 컴포넌트 재사용(로직 변경 없음). 구 선택(goGu)·검색·지도 핀 이동은 리스트 뷰로 자동 전환.

## v1.5 (2026-06-19)
- **예산 기반 단지 매칭("이 예산으로 살 수 있는 단지")**: 보유현금(+소득)으로 살 수 있는 최대 매매가를 산출하고, 그 예산 이하 청주 단지를 시세로 매칭. 단지별 '자기자본 OO + 대출 OO · 월상환 OO' 제공. 대출+시세 결합(우리만의 강점).
  - 백엔드 `loan.max_affordable_price`(estimate의 total_cash_needed 이진탐색 → 대출탭과 일관) + `stats.affordable_complexes` + `POST /loan/affordable`. 테스트 test_affordable.py.
  - 프런트: 대출 화면에 '내 예산으로 단지 찾기' 섹션(예산 헤드라인·단지 카드·탭하면 상세). 금리·기간 기준 참고치 고지.
- **버그픽스**: 단지 상세(Detail)에 v1.3 비교 토글 props(inCompare/onToggleCompare)가 시그니처에 빠져 비교 버튼이 안 뜨던 문제 수정(+ onOpen 추가).

## v1.4 (2026-06-19)
- **청약·분양 정식 탭**: 소식 탭에 섞여 있던 청약을 전용 '청약' 탭으로 분리(하단 네비 추가, 전용 아이콘).
  - 상태 필터 칩(전체/접수중/접수예정/마감, 건수 표시) + 공고 카드(단지·지역·기간·공급세대·분양가·경쟁률·최저가점·주택형별).
  - 백엔드 `GET /subscription`(청약홈 applyhome, 키 없으면 예시 폴백·live 플래그·안내·출처 고지). 테스트 test_subscription.py.
  - 소식 탭은 이제 뉴스·정책만.

## v1.3 (2026-06-19)
- **단지 비교(Compare)**: 최대 4개 단지를 나란히 비교(최근 매매가·평단가·전세가율·전고점 대비·거래량·준공·세대수). 항목별 '최적' 강조(평단가↓·전세가율↓·거래량↑·준공↑, 투자판단 아님 고지). 전세가율은 위험색 반영.
  - 백엔드 `stats.compare_one` + `POST /compare`(최대 4개, 거래 없으면 found=False). 테스트 test_compare.py.
  - 프런트: 단지 상세 '⊕ 비교' 토글 → 하단 플로팅 '비교 N개' 바 → 비교 오버레이(가로 스크롤·지표 고정열·열별 제거). 선택은 기기에 저장(safeStore).

## v1.2 (2026-06-19)
- **전세가율 위험 배지(깡통전세 안내)**: 전세가율 80%↑ '높음'·90%↑ '매우 높음' 배지+툴팁(데이터 기준·단정 아님). 안전 조회 트렌드 반영.
- **대출 안내 강화**: '회원가입·신용조회 없이 한도 미리보기(구간만 사용·조회기록 없음)' 배너. 기존 공시 면책·실시간 공시 배지 유지.
- **검색 인덱스(pg_trgm)**: PostgreSQL 부분일치 LIKE 가속 GIN 인덱스 마이그레이션 0007(타 DB는 건너뜀).
- **초기 로딩 최적화**: 홈 첫 로드 랭킹 limit 300→60(랭킹 탭은 자체 조회).
- **정리**: 미사용 `price_per_m2`(샘플) 제거, 미사용 `by_area`(단지상세) 제거, 지도 로더 스켈레톤화, 콜아웃 다크모드 토큰화(--callout-*).

## v1.1 (2026-06-19)
- **단지 데이터 보강(K-apt)**: 세대수·동수·사용승인일(연식)·난방·연면적·시공사·주차. 미설정/미매칭은 null(날조 금지). `scripts/enrich.py`·`/admin/enrich`.
- **실거래 정정·해제 반영(⑥)**: 정정=기존 행 갱신(중복 없음)·해제=집계 제외·멱등·모호 보존. 정정/해제 건수를 `/status/data`에 노출. 회귀 테스트 추가.
- **공시가격 보강**: 공식 CSV(호별)→단지·면적 중앙값 집계 임포터(`scripts/import_gongsi.py`). 청주 한정·매칭 실패 null.
- **학군(통학 접근성)**: 카카오 POI(학교)로 인근 학교 수·최단·초/중/고. 거리 기준(학업성취 아님) 명시.
- **외부 API 엔드포인트 .env화**: MOLIT·네이버/카카오·finlife·청약·뉴스·OAuth·K-apt 주소를 모두 설정값으로(빈 값이면 코드 기본값).
- **운영 가이드 OPERATIONS.md**: 설치·운영·배포·모니터링·장애대응·점검 체크리스트.
- **UI 개편**: 시세 면적별 카드 분리(+면적 미상)·모바일 행 카드·필터 고정·로딩 스켈레톤·단지 미니 스파크라인·단위 툴팁·접힘 애니메이션·터치영역·빈 상태 통일·**다크 모드**.
- **마이그레이션 체인 정리**(0001→…→0006 단일 head).

## v1.0 (기준선)
- 초기 MVP: 실거래 수집·정규화 파이프라인, 시세/대시보드/검색/단지상세/비교, 청약·뉴스, 대출 추천(동의·간이모드), 커뮤니티, 지도/POI, 알림(이메일·푸시·알림톡 토대), 인증, 관측성·레이트리밋·법적 고지·테스트/CI.
