# store/ — 스토어 등록 메타데이터 템플릿

> 앱 스토어(Google Play / App Store) 등록에 필요한 텍스트·정보 템플릿. `[대괄호]`는 운영자가 채울 값.
> ⚠️ **개인정보 라벨(Data safety / App Privacy)은 반드시 앱의 실제 동작과 일치**해야 합니다. 아래 답안은 현재 코드 기준 '추정'이며, 배포 설정(특히 대출 민감정보 저장 여부)에 따라 달라지므로 **출시 전 실제 데이터 흐름으로 검증**하세요. 불일치 시 스토어 반려·법적 리스크.

## 파일
- `google-play.md` — Google Play Console 등록 항목 + Data safety.
- `app-store.md` — App Store Connect 등록 항목 + App Privacy(영양성분표).

## 공통으로 준비할 자산(별도 디자인 필요)
- 앱 아이콘: 512×512(Play), 1024×1024(App Store). **현재 frontend/public/icons 는 플레이스홀더 — 교체 필수.**
- 스크린샷: 폰 기준 최소 2~8장(주요 화면: 대시보드·시세·단지상세·대출·중개사 대시보드). Play는 16:9 또는 9:16, App Store는 기기별 해상도.
- Play 피처 그래픽: 1024×500.
- 지원/문의 URL·이메일, 개인정보처리방침 **공개 URL**(앱 내 `/legal`와 동일 내용 웹 공개).

## 출시 전 체크
1. `python -m scripts.preflight` 통과(FAIL 0).
2. 개인정보 라벨이 실제 수집/저장과 일치하는지 검증.
3. 대출 민감정보(9.A): 저장 안 함(stateless)인지/저장 시 암호화·보유기간 명시인지 확정 → 라벨 반영.
