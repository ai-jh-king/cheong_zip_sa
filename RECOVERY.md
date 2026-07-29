# RECOVERY.md — DB 장애·유실 복구 절차

> 2026-07 실사고: Render **무료 PostgreSQL 만료**로 운영 DB 소멸.
> 백업은 컨테이너 임시 파일시스템(`./backups`)에 저장돼 재시작마다 사라져 복구용 덤프가 없었음.
> 그 경험으로 만든 절차서. **앱·프런트는 무사하고 데이터만 다시 채우면 되는 구조**라 복구는 단순하다.

---

## 0. 증상으로 원인 판별

| 확인 | 정상 | DB 장애 |
|---|---|---|
| `GET /health` | `status: ok`, `db_ok: true` | **`db_ok: false`**, `status: degraded` |
| `GET /loan/rules` (DB 무관) | 200 | 200 (앱은 살아 있음) |
| `GET /status/data`, `/map/markers` | 200 | **500** |
| 프런트 | 실거래 표시 | DEMO 폴백(백엔드 미연결 배너) |

DB 무관 엔드포인트가 200인데 DB 엔드포인트만 500이면 **애플리케이션이 아니라 DB 문제**다.
Render 대시보드 > 해당 Postgres 상태(`Available` / `Suspended` / `Expired`)와 웹 서비스 Logs의
`connection refused` / `does not exist` 메시지로 확정한다.

---

## 1. 새 DB 준비 (만료·삭제된 경우)

1. Render > New + > **PostgreSQL** 생성 — **반드시 유료 플랜**(무료는 일정 기간 후 자동 만료, 복구 불가).
   region은 서비스와 동일(`singapore`), `databaseName: cheongju`.
2. 생성된 **Internal Database URL** 복사.
3. 다음 서비스의 `DATABASE_URL` 환경변수를 새 값으로 교체:
   - 웹 서비스(`cheongju-realestate`)
   - 크론(`cheongju-collect`)
4. 웹 서비스 **Manual Deploy** — `preDeployCommand`(`python -m scripts.db_upgrade`)가 스키마를 생성한다.

> Blueprint(`render.yaml`)를 그대로 Apply 하는 경우 위 1~3은 자동. 단, 기존 서비스가 대시보드에서
> 수동 생성됐다면 중복 생성 방지를 위해 수동 교체를 권장.

---

## 2. 데이터 복구 — 한 줄

웹 서비스 **Shell**(유료 플랜)에서:

```bash
python -m scripts.bootstrap
```

순서대로 실행되며 각 단계는 멱등이고, 하나가 실패해도 나머지는 계속된다.

| 단계 | 내용 | 실패해도 되는가 |
|---|---|---|
| 마이그레이션 | Alembic head까지 스키마 생성 | ❌ 필수 |
| 도감 시드 | 집사 도감 시리즈·편(7편) | ✅ 부팅 시 자동 시드도 있음 |
| 개발호재 시드 | 청주 개발 이슈(홈·지도 핀) | ✅ 해당 UI만 숨김 |
| 통근거점 시드 | SK하이닉스 등 직장·산단 | ✅ 부팅 시 자동 시드도 있음 |
| 실거래 수집 | MOLIT 실거래(시세·지도·랭킹의 원천) | ❌ 사실상 필수(키 필요) |
| 지오코딩 | 단지 좌표(지도 마커) | ✅ 카카오 키 없으면 자동 건너뜀 |
| 집계 스냅샷 | 첫 로드 속도용 프리컴퓨트 | ✅ 없으면 라이브 계산 |

Shell을 못 쓰는 플랜이라면 크론(`cheongju-collect`)의 `dockerCommand`를 임시로
`python -m scripts.bootstrap` 으로 바꿔 1회 수동 실행 후 되돌린다.
또는 관리자 화면(`/admin/monitor`)에서 **수집+지오코딩** 버튼으로 대체 가능(시드는 부팅 자동분에 의존).

### 소요 시간(참고)
- 마이그레이션·시드: 수십 초
- 실거래 수집: 개월 수·API 응답에 따라 수 분~수십 분
- 지오코딩: 단지 1,000곳 기준 수 분(주소 기반)

---

## 3. 복구 확인

```bash
curl -s https://<도메인>/health        # db_ok: true
curl -s https://<도메인>/status/data   # 200 + 건수
```
앱에서 홈 진입 → 배너·구별 시세·지도 마커가 표시되면 완료.
`python -m scripts.doctor` 로 키·설정 자가진단도 함께 수행 권장.

---

## 4. 재발 방지 (이미 반영됨)

- `render.yaml`: DB **유료 플랜** 고정 + 크론에 **영구 디스크**(`/var/backups/cheongju`) 마운트 및
  `BACKUP_DIR` 지정 — 백업 파일이 재시작에도 남는다.
- 백업 확인: `python -m scripts.backup --list` (스케줄러가 주기 실행, 최근 N개 보관)
- 복구(덤프가 있을 때): `python -m scripts.restore <파일>` — 자세한 절차는 `OPERATIONS.md`.
- 모니터링: `/health`의 `db_ok`를 외부 업타임 모니터(예: UptimeRobot)로 감시하면 즉시 인지 가능.
