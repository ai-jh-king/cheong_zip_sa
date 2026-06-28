# 프런트엔드·UI 컨벤션 (app/web/index.html) — skills

## 구조
- **단일 파일**: `index.html` 하나에 React 18 + Babel(CDN), Pretendard 폰트. 빌드 없음.
- 백엔드 미연결/오프라인이면 **DEMO 폴백**(`DEMO_TX`, `demoBoard()`, `demoRanking()`, `demoDetail()`, `demoHeatmap()`)으로 동작. 폴백 데이터는 항상 `is_sample/모의` 배지.
- API 베이스 `API`. 모든 fetch는 `.catch(()=>폴백)`로 감싼다(앱이 안 깨지게).

## ⚠️ 절대 규칙: 렌더 안에서 컴포넌트 정의 금지
> 예외(허용): 리스트 항목을 인라인으로 그릴 땐 **컴포넌트가 아니라 "JSX를 반환하는 렌더 함수"**(예: `renderCmt(c, reply)`)를 쓴다. 새 컴포넌트 타입이 아니므로 리마운트가 없어 입력 포커스가 유지된다. (커뮤니티 댓글/대댓글이 이 패턴)

- 입력 컴포넌트(예: `LoanField`, `Sel`)를 **부모 함수 안에서 정의하면** 매 렌더마다 새 함수 → React가 언마운트/리마운트 → **입력 포커스가 빠진다**(한 글자마다 끊김).
- 반드시 **모듈 레벨**에 정의하고 props로 값을 받는다. (과거 Loan의 `Field` 내부 정의가 이 버그를 유발 → `LoanField`로 분리해 해결.)

## 상태·동기화
- `device_id`는 `safeStore`(localStorage→메모리 폴백). 개인화는 device 스코프 fetch + **낙관적 업데이트 + best-effort PUT/POST**.
- 단위(㎡/평)는 `UnitCtx` + `useUnit()` + `fmtArea(m2, unit)`. 설정은 `/me/prefs`에 저장(`prefsLoaded` ref로 초기 로드 중 덮어쓰기 방지).
- 탭 전환은 `tab` 상태. 구 클릭 이동은 `goGu(guName)`(→ 시세 탭 + 해당 구 필터).

## 디자인 토큰
- 배경: 은은한 그라데이션(민트→라벤더), 카드는 **반투명+blur(frosted)**.
- 브랜드 `TEAL=#0F766E`(= CSS `--teal`). 헤더는 jade-teal 그라데이션.
- 등락색: 상승 `UP=#C8322A`(▲), 하락 `DOWN=#1E5FC4`(▼). `MUTED/INK` 보조.
- 구 색상 `GU_COLORS`(상당 파랑/서원 주황/흥덕 초록/청원 보라) — 그래프·막대·헤더 공통.

## 넘침·정렬 방지
- 숫자는 `.num{white-space:nowrap}`(금액 줄바꿈 방지). 가격 칸은 `flex:none`.
- 가변 영역은 `minWidth:0` + `overflow:hidden;textOverflow:ellipsis`. 제목 길면 `overflowWrap:anywhere`.
- 한 줄에 몰아넣지 말고 `flexWrap:wrap` 허용. 표는 `overflowX:auto` 래핑, 컬럼 폭 지정.

## 차트(의존성 없는 SVG)
- `DetailLine`(단일선), `MultiLine`(구별 다중선+범례, 빈 달 끊기). 좌표 변환 `X(i)/Y(v)`, y축 3틱.
- 지도: **네이버 지도 v3**(`?ncpKeyId=`, `useNaver` 훅, `navermap_authFailure` 처리). 지오코딩은 **네이버 우선**(+카카오 폴백), 인근 POI(반경 카테고리)는 카카오(네이버 동등 API 없음).

## 검증 루틴(매 수정)
1. babel 스크립트 블록 괄호 균형 `() {} []`.
2. 미정의 `<Capitalized>` 컴포넌트 0개.
3. `outputs/cheongju-ui.html`로 복사 후 재압축.

## 접이식 카드 / 시세 섹션
- `Collapsible({title,right,defaultOpen,children})` — 공통 접기/펼치기 카드(헤더 클릭 토글, ▾ 회전). 새 섹션은 이걸로 감싼다.
- 시세 탭: 거래유형 필터 제거 → **매매/전세/월세 `DealSection` 3개**(각 자체 페이징 5건 + 거래유형별 Histogram bare). 매매만 기본 펼침.
- ⚠️ 상태(페이지·열림)를 가진 섹션 컴포넌트는 **모듈 레벨**에 정의(렌더 내 정의 금지=리마운트).

## 랭킹 묶기/펼치기
- 매매가·평단가 순위는 `rankGroups`로 **같은 단지+면적(반올림㎡) 묶음** → 대표값=중앙값. `RankGroups`는 탭하면 개별 거래(날짜·층·가격) 펼침. 단독(무단지명)은 개별 유지.
- 대장아파트 TOP5는 홈 '구별 매매추이' 위 섹션.

## 전 섹션 접기/펼치기(전체 적용)
- 홈·소식·단지상세·랭킹지도·대출결과·관심/최근 등 **모든 주요 카드 섹션을 `Collapsible`로 통일**(기본 `defaultOpen={true}`). 헤더 클릭 토글.
- `SecTitle`은 더 이상 사용 안 함(정의는 유지). 새 섹션도 `<Collapsible icon title defaultOpen>…</Collapsible>` 패턴 사용.

## 단지 상세 = (아파트 × 면적)
- 상세는 단지 요약(전체 최근가·전세가율·면적타입 수) + **면적별 `AreaSection`**(최근가·중앙값·전저점/전고점·전세가율·평단가·면적 추이·최근거래)로 구성.
- **층별/면적별 평단가 섹션 제거**, 단지 전체 추이·전체 최근거래 제거(면적 단위로 흡수).
- **대출 탭 삭제** → 상세 하단 `대출 계산` 접이식에 통합. `<Loan initialPrice=면적최근가/>`, 면적 칩/‘이 면적으로 대출 계산→’ 버튼으로 매매가 자동 입력(선택 시 key 변경→펼침+재초기화).
- 백엔드 `complex_detail.areas`(=_area_block) 사용. 데모 `demoDetail`도 동일 areas 제공.

## 매물 사진 스토리지 + floating 뒤로
- 사진은 폼에서 `POST /listings/upload`(multipart)로 보내 **외부/로컬 스토리지 URL**을 받아 photos에 저장(원본 base64 미저장). 실패 시 데이터URL 폴백(오프라인 미리보기).
- 스토리지는 `app/services/storage.py`가 설정 `storage_backend`(local|s3)로 분기. local은 `/uploads` 정적 서빙, s3는 boto3(지연 import). 키는 .env.
- `BackBtn`을 **floating pill**(position:fixed, 좌하단, nav 위)로 재정의 → 상세·매물등록·매물상세 전부 일관 적용.

## UX 컴포넌트/테마 (2026-06 개편)
- 색상 토큰은 CSS 변수: JS 상수 `INK/MUTED/TEAL/UP/DOWN/LINE = var(--*)`. CSS `:root`(라이트)+`[data-theme=dark]` 오버라이드. 헤더 🌙/☀️ 토글이 `document.documentElement.dataset.theme` 설정+safeStore 저장.
- 표면 변수: `--surface`(.card), `--surface-solid`(모달/플로팅), `--surface-2`(입력/네비/토글), `--chip`(칩/세그먼트), `--bg1/2/3`(본문 그라데이션), `--row/--hd`(행/헤더), `--line`.
- 공용 컴포넌트: `Skeleton`/`SkeletonCard`(로딩), `Info`(`.tip` 툴팁), `Sparkline`(미니 막대 추이).
- 시세 리스트(BandList)는 표 대신 `.txrow` 행 카드(모바일 가독성). 면적대(소형/중형/대형/면적 미상)별 카드 분리, 빈 면적대 숨김.
- 시세 필터는 `.sticky-filter`(상단 고정). Collapsible 본문은 `.collapse-body` 등장 애니메이션. 탭/토글 최소 터치영역(min-height) 보장.
- Empty 는 `action` 프롭으로 행동유도 버튼 지원(예: 검색 결과 없음 → '검색어 지우기').
- 인라인 색상 추가 시 하드코딩 hex 금지 → 위 변수 사용(다크모드 유지). 강조 배지(브랜드/콜아웃)는 의도적으로 고정색 유지 가능.
- 비교(Compare): App `compare` 상태(safeStore 'cj_compare'), `inCompare`/`toggleCompare`. 단지 상세 '⊕ 비교' 토글 → 플로팅 바 → `CompareOverlay`(POST /compare). 지표 행×단지 열, 첫 열/헤더 sticky, 열별 ✕ 제거, '최적' 강조는 단순 비교(투자판단 아님).
- 네비(6탭): 홈·시세·청약·매물·게시판·소식. '시세'는 PriceHub 래퍼가 리스트(Price)·지도(HeatTab)·랭킹(Rank)을 상단 토글로 묶음(priceView 상태). 랭킹/지도는 더 이상 별도 탭 아님. goGu는 priceView를 list로 리셋.

## 시세 탭(PriceHub) 구조
- PriceHub가 **유형(property_type)을 공유 상태**로 보유 → 리스트(Price)/지도(HeatTab)/랭킹(Rank)에 prop으로 전달. 유형 변경 시 onType(loadRanking)로 랭킹 재요청, HeatTab은 prop 의존 useEffect로 재fetch.
- '전체 유형'은 리스트만 지원, 지도·랭킹은 아파트로 폴백(안내 표기).
- 뷰 토글(list/map/rank)은 한 번에 하나만 렌더 → 길이 억제. 구 클릭 → goGu 드릴다운.


## 바텀시트 통일 (SheetShell) — 모든 상세/오버레이 공통
- 단지·매물·게시판·청약·통근·예산·검색 상세는 **공용 `SheetShell({onClose,zIndex,header,scrollKey,children})`** 하나로 통일. ReactDOM.createPortal(body), maxWidth480 중앙, height 93vh, 핸들+선택적 header+스크롤 본문.
- **아래로 스와이프 닫기**: 스크롤이 맨 위(scrollTop≤0)일 때 아래로 끌면 시트가 따라 내려가고 110px 이상 시 onClose, 미만이면 transition으로 복귀. 내부 스크롤/버튼과 충돌 방지 위해 '맨 위에서 아래로'일 때만 드래그 인식. dim 배경 탭·핸들로도 닫힘.
- 각 시트는 얇은 래퍼: `DetailSheet`(단지)·`ListingSheet`(매물)·`PostSheet`(게시판)·`SubSheet`(청약)·`CommuteSheet`·`BudgetSheet`·검색(SearchOverlay가 SheetShell 사용). 내부는 해당 상세 컴포넌트를 그대로 렌더(예: `<Detail onBack={onClose}/>`).
- **상세에는 별도 '뒤로(‹)' 버튼을 두지 않는다**(시트 닫기로 충분). 전체화면 폼(매물 등록)·작성자 보기만 BackBtn 유지.
- 탭에서 상세를 띄울 땐 **리스트를 유지한 채 오버레이**(전체화면 전환 금지): `{sel&&<XxxSheet .../>}`를 리스트와 함께 렌더.

## 시세 탭 (지역→단지 드릴다운)
- `PriceHub`: 구 칩(전체·상당·서원·흥덕·청원) → 구 요약 카드(평균 매매 중앙·전월등락·전세가율·거래량) → 단지 리스트(거래 많은 순 기본). 평형·유형·정렬은 '상세 ▼'로 접음. 서브탭=리스트/지도(랭킹 제거, 홈과 중복).
- 데이터는 **서버 `/price/overview`**(aggregations.md). `demo` prop(=status==="demo")이면 요청 생략하고 `demoOverview` 즉시 사용(미리보기 지연 제거), live면 fetch + **4초 AbortController 타임아웃** 후 폴백. 로딩 중 직전 결과 유지 + '불러오는 중…'.

## 단지 상세 부가 위젯(데이터 근거·왜곡 없음)
- `LivingScore`(생활권 점수, d.living_score) · `FairPriceCheck`(적정가 체크, a.amounts 중앙값 대비) · `VolumeSignal`(거래 동향, d.volume 최근3개월 vs 직전3개월) · `ExternalListings`(네이버 검색/지도 링크, 비제휴 고지) · 신고가 배지. 모두 "참고용" 고지 + 표본/좌표 없으면 미표시(None).

## 임장 도우미 (TourSheet)
- 홈 '관심 단지'의 🧭 버튼 → `TourSheet`(SheetShell). 관심 단지를 순번 코스로 나열, 단지별 `TourStop`에 임장 체크리스트(9항목)+메모. 체크/메모는 **safeStore 로 기기에만 저장**(키 `cj_tour_<target_id>`, 서버 전송 없음).

## 푸시 토글 (PushToggle)
- 알림함(NotificationsOverlay) 상단. `enablePush()`(권한요청→/sw.js 등록→pushManager.subscribe(VAPID 공개키)→/push/subscribe 저장)·`disablePush()`. `serviceWorker`/`PushManager`/`Notification` 미지원 시 숨김. 도우미 함수는 모듈 레벨(authHeader 아래).

## 데모/오프라인 폴백 규칙(보강)
- 새 화면이 백엔드를 호출하면 반드시 `demoXxx()` 폴백을 같은 형상으로 제공하고 `.catch`에서 사용. `status`(loading|live|demo)를 활용해 demo면 요청 자체를 생략(불필요한 실패 대기 방지). catch 가드는 `if(!on)return`(언마운트 가드) — 부호 실수 주의.

## 공유·SEO 진입 페이지 (api/landing.py) — SPA와 별개
- SPA(`/`)는 그대로 두고, 백엔드가 **서버 렌더 진입 페이지**를 추가 제공: `/r/{lawd_cd}`(지역)·`/c/{lawd_cd}/{name}`(단지). 목적: ① 구글 색인 ② 카카오톡/링크 공유 OG 미리보기 ③ SPA 재작성 없이.
- 각 페이지: `<title>`+`description`+Open Graph(og:title/description/url)+Twitter card + 핵심 시세(중앙값·전세가율·거래수) + "앱에서 보기" CTA(→`/`). 데이터 없으면 '수집 중' 안전 표기, **모든 동적 문자열 html.escape**(인젝션 방지).
- 데이터: stats.price_overview(지역)·complex_detail(단지) 재사용. 절대 URL은 `PUBLIC_BASE_URL`(없으면 요청 호스트 추론).
- `/sitemap.xml`(지역+주요 단지 최대 30/구)·`/robots.txt` 제공. 단지명은 URL quote, 페이지에선 escape.
- 향후: og:image 동적 생성, SPA 딥링크(공유 링크 탭 시 해당 단지로 바로 진입), 단지/지역 페이지에서 앱 설치 유도.
