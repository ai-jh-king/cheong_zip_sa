"""
데이터 모델 (M1 범위: Region / Complex / Transaction).
지침서 5장 데이터 모델을 정규화 가이드로 삼되, '왜곡 없음'을 위해
모든 레코드에 출처(source)·원본보존(raw_payload)·수집시각을 남긴다.

PriceStat / Subscription / News / LoanProduct / LoanRule 등은
해당 마일스톤(M2~M4)에서 추가한다. 여기선 토대만.
"""
from datetime import datetime, date

from sqlalchemy import (
    String, Integer, Float, Date, DateTime, ForeignKey, JSON, Boolean, Index, UniqueConstraint, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Region(Base):
    __tablename__ = "regions"

    lawd_cd: Mapped[str] = mapped_column(String(5), primary_key=True)  # 법정동 앞5자리
    sido: Mapped[str] = mapped_column(String(20), default="충청북도")
    sigungu: Mapped[str] = mapped_column(String(40))                   # 청주시 OO구
    dong: Mapped[str | None] = mapped_column(String(40), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="region")


class Complex(Base):
    """단지(아파트/오피스텔) 또는 건물 단위. 비아파트는 단지 개념이 약해 nullable 다수."""
    __tablename__ = "complexes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    lawd_cd: Mapped[str] = mapped_column(String(5), ForeignKey("regions.lawd_cd"))
    # 법정동 — 같은 구(區)에 동명(同名) 단지가 여러 동에 존재(예: 흥덕구 '대원' 가경동/복대동).
    # (name, lawd_cd)만으로는 서로 다른 단지가 1행으로 합쳐져 좌표·시세가 섞임(v1.224 교정).
    # 신규 행은 동 단위로 생성·지오코딩. 레거시 행(dong=None)은 동이 유일할 때만 좌표 사용.
    dong: Mapped[str | None] = mapped_column(String(40), nullable=True)
    property_type: Mapped[str] = mapped_column(String(20))  # apartment/officetel/rowhouse/detached
    build_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    households: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # --- 단지 기본정보 보강(공동주택관리정보 K-apt) — 없으면 null(왜곡 방지) ---
    kapt_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dong_count: Mapped[int | None] = mapped_column(Integer, nullable=True)      # 동수
    heating: Mapped[str | None] = mapped_column(String(40), nullable=True)      # 난방방식
    total_area: Mapped[float | None] = mapped_column(Float, nullable=True)      # 연면적(㎡)
    builder: Mapped[str | None] = mapped_column(String(120), nullable=True)     # 시공사
    approval_date: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 사용승인일(YYYYMMDD/원문)
    parking: Mapped[int | None] = mapped_column(Integer, nullable=True)         # 총주차대수
    price_official: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 공동주택 공시가격(만원, 단지·면적 중앙값)
    price_basis_date: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 공시기준일
    meta_source: Mapped[str | None] = mapped_column(String(40), nullable=True)  # 예: KAPT
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_complex_region_name_type", "lawd_cd", "name", "property_type"),
    )


class Transaction(Base):
    """
    정규화된 실거래 1건. 유형(아파트/오피스텔/빌라/단독)·거래유형(매매/전월세) 공통 스키마로 흡수.
    유형별 응답 필드 차이는 normalize 단계에서 이 공통 형태로 매핑한다.
    """
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lawd_cd: Mapped[str] = mapped_column(String(5), ForeignKey("regions.lawd_cd"))
    complex_id: Mapped[int | None] = mapped_column(ForeignKey("complexes.id"), nullable=True)

    property_type: Mapped[str] = mapped_column(String(20))   # apartment/officetel/rowhouse/detached
    deal_type: Mapped[str] = mapped_column(String(10))       # trade(매매)/jeonse(전세)/wolse(월세)

    complex_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    dong_name: Mapped[str | None] = mapped_column(String(40), nullable=True)  # 법정동명
    exclusive_area: Mapped[float | None] = mapped_column(Float, nullable=True)  # 전용면적 ㎡
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    build_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    contract_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # 계약일
    deal_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 매매가(만원)
    deposit: Mapped[int | None] = mapped_column(Integer, nullable=True)      # 보증금(만원)
    monthly_rent: Mapped[int | None] = mapped_column(Integer, nullable=True) # 월세(만원)

    # --- 출처/무결성 (왜곡 방지) ---
    source: Mapped[str] = mapped_column(String(40))          # 예: MOLIT_APT_TRADE / FIXTURE
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)  # 개발용 모의데이터 표식
    dedup_key: Mapped[str] = mapped_column(String(200), unique=True) # 중복 적재 방지(금액 포함)
    identity_key: Mapped[str | None] = mapped_column(String(220), nullable=True, index=True)  # 계약식별(금액 제외)→정정/해제 매칭
    is_canceled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # 해제(취소)분 — 집계 제외
    canceled_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # 해제사유발생일
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # 정정으로 금액 갱신된 시각
    trade_method: Mapped[str | None] = mapped_column(String(12), nullable=True)  # 거래유형 'agent'(중개)/'direct'(직거래)/None
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 원본 보존
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    region: Mapped["Region"] = relationship(back_populates="transactions")

    __table_args__ = (
        Index("ix_tx_region_month", "lawd_cd", "contract_date"),
        Index("ix_tx_type_deal", "property_type", "deal_type"),
        Index("ix_tx_active", "property_type", "is_canceled"),
        # 부하 감사 H2: 단지상세·호가검증·급매 등 핫패스가 complex_name 등가조건 풀스캔이던 것
        Index("ix_tx_complex_lawd", "complex_name", "lawd_cd"),
    )


class Favorite(Base):
    """관심 등록(즐겨찾기). 익명 device_id 기준 — 개인정보 없음(M5)."""
    __tablename__ = "favorites"
    __table_args__ = (Index("ix_fav_device", "device_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[str] = mapped_column(String(20))   # complex | region
    target_id: Mapped[str] = mapped_column(String(200))    # name__lawd__type 등 식별자
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 표시·재진입용(gu/dong/type/lawd_cd)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserPref(Base):
    """기기별 개인화 설정(익명 device_id). 단위/내 동네/기본 유형 등 JSON 1행."""
    __tablename__ = "user_prefs"
    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RecentView(Base):
    """최근 본 단지(익명 device_id). 최신순, 기기당 상한 유지."""
    __tablename__ = "recent_views"
    __table_args__ = (Index("ix_recent_device", "device_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    target_id: Mapped[str] = mapped_column(String(200))
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    viewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SavedSearch(Base):
    """저장된 검색(익명 device_id). 시세 필터(구/유형/거래/평형/정렬) JSON 보관."""
    __tablename__ = "saved_searches"
    __table_args__ = (Index("ix_saved_device", "device_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Account(Base):
    """개인화 2단계: 소셜 로그인 계정(구조 준비).
    role: user(일반-매수/매도) | agent(중개업자). 향후 매물·거래 기능의 권한 기준."""
    __tablename__ = "accounts"
    __table_args__ = (Index("ix_account_provider", "provider", "provider_uid", unique=True),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(20))          # kakao | naver
    provider_uid: Mapped[str] = mapped_column(String(120))     # 공급자 고유 식별자
    role: Mapped[str] = mapped_column(String(20), default="user")
    plan: Mapped[str] = mapped_column(String(20), default="free")          # free | premium (부록B 게이팅·기본 free)
    nickname: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DeviceLink(Base):
    """기기(device_id) ↔ 계정(account_id) 연결. 로그인 시 익명 데이터를 계정으로 승격."""
    __tablename__ = "device_links"
    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, index=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Listing(Base):
    """등록 매물(UGC) — 사용자/중개업자가 올린 매물. 실거래(Transaction)와 '분리'한다(왜곡 방지).
    「중개대상물의 표시·광고 명시사항 세부기준」(국토부 고시)의 명시 항목을 컬럼으로 담는다.
    실거래가 아님 → is_sample/검증여부와 무관하게 '등록매물'로 표기·노출한다."""
    __tablename__ = "listings"
    __table_args__ = (
        Index("ix_listing_region_deal", "lawd_cd", "deal_type"),
        Index("ix_listing_created", "created_at"),
        Index("ix_listing_account", "account_id"),   # 부하 감사 L1: 내 매물 필터·로그인 흡수
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 등록 주체
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    poster_role: Mapped[str] = mapped_column(String(20), default="user")   # user | agent
    is_sponsored: Mapped[bool] = mapped_column(Boolean, default=False)      # 광고/제휴 노출(부록B·기본 False=현재와 동일)
    priority: Mapped[int] = mapped_column(Integer, default=0)               # 노출 우선순위(높을수록 위, 기본 0)
    views: Mapped[int] = mapped_column(Integer, default=0)                  # 상세 조회수(외부 조회만 집계·소유자 제외)

    # 매물 기본
    title: Mapped[str] = mapped_column(String(120))
    deal_type: Mapped[str] = mapped_column(String(10))        # trade/jeonse/wolse
    property_type: Mapped[str] = mapped_column(String(20))    # apartment/officetel/rowhouse/detached/oneroom

    # 소재지(명시: 읍·면·동까지. 지번·동·호 표시 의무 아님 → 상세주소는 비공개 가능)
    lawd_cd: Mapped[str] = mapped_column(String(5))
    dong_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    complex_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address_detail: Mapped[str | None] = mapped_column(String(200), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 면적/구조(명시: 전용/공급면적, 해당층/총층, 방향, 방·욕실 수)
    exclusive_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    supply_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    baths: Mapped[int | None] = mapped_column(Integer, nullable=True)
    direction: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # 가격(만원 단위)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)        # 매매가 / 전세보증금
    deposit: Mapped[int | None] = mapped_column(Integer, nullable=True)      # 월세 보증금
    monthly_rent: Mapped[int | None] = mapped_column(Integer, nullable=True) # 월세
    maintenance_fee: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 관리비(만원/월)
    maintenance_items: Mapped[str | None] = mapped_column(String(200), nullable=True)  # 관리비 포함내역

    # 기타 명시(입주가능일, 준공일) + 옵션/설명/사진
    move_in_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    approval_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    options: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    photos: Mapped[list | None] = mapped_column(JSON, nullable=True)  # URL 또는 데이터URL 리스트

    # 중개업체 정보(명시 의무: 사무소 명칭·소재지·연락처·등록번호·중개사 성명)
    agent_office: Mapped[str | None] = mapped_column(String(120), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    agent_reg_no: Mapped[str | None] = mapped_column(String(40), nullable=True)
    agent_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    agent_address: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # 메타
    status: Mapped[str] = mapped_column(String(20), default="active")   # active/traded/hidden
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Post(Base):
    """커뮤니티 게시글 — 사용자 소통(부동산 의견/질문/정보/지역소식).
    ⚠️ 실거래·공식정보가 아님(사용자 작성). 가격·전망 등은 개인 의견."""
    __tablename__ = "posts"
    __table_args__ = (
        Index("ix_post_cat_created", "category", "created_at"),
        Index("ix_post_created", "created_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nickname: Mapped[str | None] = mapped_column(String(40), nullable=True)
    category: Mapped[str] = mapped_column(String(20), default="free")   # free/qa/info/deal/local
    title: Mapped[str] = mapped_column(String(150))
    body: Mapped[str] = mapped_column(String(8000))
    lawd_cd: Mapped[str | None] = mapped_column(String(5), nullable=True)  # 지역 태그(선택)
    complex_name: Mapped[str | None] = mapped_column(String(120), nullable=True)  # @단지 연결(선택)
    resident: Mapped[bool] = mapped_column(Boolean, default=False)  # 작성 시점 "우리집=이 단지" 서버 검증 결과(자가 등록 기반 주민 표시)
    property_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 단지 유형(연결 시)
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)  # 첨부 이미지 URL 리스트
    views: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    report_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")   # active/hidden
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Comment(Base):
    """게시글 댓글."""
    __tablename__ = "comments"
    __table_args__ = (Index("ix_comment_post", "post_id", "created_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(Integer, index=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # 대댓글(1단계)
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(40), nullable=True)
    body: Mapped[str] = mapped_column(String(2000))
    report_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PostLike(Base):
    """좋아요(중복 방지: post_id+owner). owner = device_id 또는 acct:<id>."""
    __tablename__ = "post_likes"
    __table_args__ = (UniqueConstraint("post_id", "owner", name="uq_post_like"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(Integer, index=True)
    owner: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReportLog(Base):
    """신고(중복 방지: target+owner). 임계치 도달 시 자동 숨김."""
    __tablename__ = "report_logs"
    __table_args__ = (UniqueConstraint("target_type", "target_id", "owner", name="uq_report"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_type: Mapped[str] = mapped_column(String(10))   # post | comment
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    owner: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """알림 — 내 글/댓글에 대한 반응(댓글·답글). 수신자 account_id 기준."""
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notif_acct", "account_id", "created_at"),
                      Index("ix_notif_unread", "account_id", "is_read"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, index=True)   # 수신자
    type: Mapped[str] = mapped_column(String(20))                  # comment | reply | transaction
    post_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    complex_name: Mapped[str | None] = mapped_column(String(120), nullable=True)   # transaction: 단지 이동용
    lawd_cd: Mapped[str | None] = mapped_column(String(5), nullable=True)
    property_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    actor_nickname: Mapped[str | None] = mapped_column(String(40), nullable=True)
    message: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Bookmark(Base):
    """게시글 스크랩(북마크). owner = acct:<id> 또는 device_id."""
    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("owner", "post_id", name="uq_bookmark"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(80), index=True)
    post_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppMeta(Base):
    """영속 메타(키-값). 알림 커서·관측성 워터마크 등 운영 상태 저장용."""
    __tablename__ = "app_meta"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AggSnapshot(Base):
    """일일 집계 스냅샷(프리컴퓨트). 무거운 대시보드 집계를 요청 경로에서 제거.
    데이터는 하루 1회(수집)만 바뀌므로 매 요청 계산은 낭비 → cron 수집 후 구워 저장,
    웹은 읽기 1회. payload=JSON, data_version 불일치(수집 뒤 미갱신) 시 라이브 폴백.
    value 는 대형 JSON 이라 Text(무제한). app_meta(String200)로는 부족."""
    __tablename__ = "agg_snapshot"
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    payload: Mapped[str] = mapped_column(Text)
    data_version: Mapped[int] = mapped_column(Integer, default=0)
    baked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Consent(Base):
    """동의 이력 — 개인정보 처리(특히 대출 민감정보) 동의의 버전·시각 기록(개인정보보호법 9.A)."""
    __tablename__ = "consents"
    __table_args__ = (Index("ix_consent_owner", "owner", "kind"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(80), index=True)   # acct:<id> | device_id
    kind: Mapped[str] = mapped_column(String(40))                # privacy_loan | terms | ...
    policy_version: Mapped[str] = mapped_column(String(40))
    agreed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CommuteDestination(Base):
    """통근권 검색용 목적지(직장·교통·공공시설 등).

    운영 원칙: 코드 수정 없이 운영자가 추가/비활성. 좌표는 '실제'만 사용하며,
    주소만 있고 좌표가 없으면 지오코딩 전까지 검색에서 제외(왜곡 없음).
    """
    __tablename__ = "commute_destinations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)        # 안정 슬러그(예: osong_station)
    name: Mapped[str] = mapped_column(String(80))                    # 표시명(예: 오송역)
    category: Mapped[str] = mapped_column(String(20))                # transit/job/public/education/medical
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gu: Mapped[str | None] = mapped_column(String(20), nullable=True)
    coord_method: Mapped[str | None] = mapped_column(String(20), nullable=True)  # seed_approx/geocoded/manual
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CommuteTime(Base):
    """(단지 × 목적지 × 수단) 통근시간 사전계산 캐시.

    - 'N분 이내' 검색을 빠르게 하기 위한 캐시. 배치(scripts.compute_commute)로 채움.
    - method: 'api'(길찾기 실측) / 'haversine'(직선거리 추정) — 정확도 라벨(왜곡 없음).
    - computed_at + settings.commute_cache_ttl_days 로 신선도 관리(지나면 재계산 대상).
    """
    __tablename__ = "commute_times"
    __table_args__ = (
        UniqueConstraint("complex_id", "destination_id", "mode", name="uq_commute"),
        Index("ix_commute_dest_mode_min", "destination_id", "mode", "minutes"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complex_id: Mapped[int] = mapped_column(Integer, ForeignKey("complexes.id"), index=True)
    destination_id: Mapped[int] = mapped_column(Integer, ForeignKey("commute_destinations.id"), index=True)
    mode: Mapped[str] = mapped_column(String(10))                    # car/transit/walk
    minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    method: Mapped[str] = mapped_column(String(12))                  # api/haversine
    source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PushSubscription(Base):
    """웹푸시(및 향후 FCM/APNs) 구독 정보. 채널 무관 구조.

    - webpush: endpoint + p256dh + auth (브라우저 PushManager 구독).
    - fcm/apns(후행): token 사용.
    device_id 는 항상 저장(익명 기준). 로그인 상태면 account_id 도 저장 →
    관심 단지 신고가·실거래 알림을 해당 계정의 구독으로 발송.
    endpoint(또는 token) 기준 멱등 upsert. 만료(404/410) 시 disabled 처리.
    """
    __tablename__ = "push_subscriptions"
    __table_args__ = (
        Index("ix_push_device", "device_id"),
        Index("ix_push_account", "account_id"),
        UniqueConstraint("endpoint", name="uq_push_endpoint"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(12), default="webpush")  # webpush|fcm|apns
    endpoint: Mapped[str] = mapped_column(String(500))
    p256dh: Mapped[str | None] = mapped_column(String(200), nullable=True)
    auth: Mapped[str | None] = mapped_column(String(100), nullable=True)
    token: Mapped[str | None] = mapped_column(String(400), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_ok_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)


class JobRun(Base):
    """배치 작업 실행 이력 — 수집/지오코딩/알림 등의 성공·실패·소요·통계.

    관측성의 핵심: '수집이 돌았는가/실패했는가/며칠째 안 됐는가'를 추적.
    실패 시 monitoring.alert 로 경보. 오래된 행은 운영자가 주기적으로 정리(또는 보존).
    """
    __tablename__ = "job_runs"
    __table_args__ = (Index("ix_jobrun_name_started", "name", "started_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(40), index=True)     # collect_live | geocode | notify ...
    status: Mapped[str] = mapped_column(String(12))               # running | ok | fail | partial
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Inquiry(Base):
    """매물 문의(리드) — 사용자가 등록 매물에 남기는 문의. 중개사 대시보드의 '리드'.

    개인정보(왜곡 없음·9.A 준용):
    - 연락처(contact)는 중개사 응대를 위해 저장한다(stateless 불가). 최소 항목만 수집.
    - 작성자 동의(consent=True) 없이는 생성 거부. 매물 소유자만 열람 가능.
    - 마케팅·제3자 제공 금지. 보유기간·삭제는 운영정책/처리방침에 따름.
    - 본 서비스는 게시판이며 중개행위가 아님. '문의=계약 보장' 아님.
    """
    __tablename__ = "inquiries"
    __table_args__ = (
        Index("ix_inquiry_owner_acc", "owner_account_id"),
        Index("ix_inquiry_owner_dev", "owner_device_id"),
        Index("ix_inquiry_listing", "listing_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(Integer, index=True)
    # 소유자 비정규화(대시보드 '내 리드' 조회용 — 매물 조인 없이)
    owner_account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 문의자(익명 device 기반)
    inquirer_device_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    contact: Mapped[str] = mapped_column(String(120))         # 연락처(민감) — 소유자만 열람
    message: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="new")   # new/read/contacted/closed
    consent: Mapped[bool] = mapped_column(Boolean, default=False)    # 연락처 전달 동의
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Subscription(Base):
    """구독(결제) — 유료 플랜 상태. 결제/구독 시스템은 feature_billing OFF가 기본(현재와 동일).

    - 실제 PG 없이도 mock provider로 흐름 검증 가능. provider_ref=PG 주문/결제 식별자.
    - 권한 판정은 entitlement.is_premium 에서 (플래그 ON + active 구독)일 때만 인정.
    """
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_sub_account", "account_id"),
        Index("ix_sub_status", "status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, index=True)
    plan: Mapped[str] = mapped_column(String(40), default="agent_pro")
    status: Mapped[str] = mapped_column(String(20), default="active")   # active/canceled/expired
    provider: Mapped[str] = mapped_column(String(20), default="mock")    # mock/toss/portone
    provider_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 결제 금액(원)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Place(Base):
    """생활·교육·운동 시설(공공데이터 기반 + 향후 업체 등록).

    학원·체육시설·도서관·병원 등을 하나의 모델로 normalize 한다. source 로 공공/등록/광고를
    구분해, 나중에 업체 직접 등록·홍보를 같은 테이블에 얹는다(재작업 방지 — 부록 B 원칙).
    좌표 없으면 거리/지도에서 제외(왜곡 방지). 공개 안 된 값은 null.
    """
    __tablename__ = "places"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    category: Mapped[str] = mapped_column(String(24), index=True)      # 대분류: education/sports/living
    subcategory: Mapped[str] = mapped_column(String(32), index=True)   # academy_exam/academy_lang/academy_art/academy_pe/academy_etc/library/hospital/pharmacy/sports/daycare ...
    course: Mapped[str | None] = mapped_column(String(150), nullable=True)        # 교습과정/종목 원문(분류 근거·표시용)
    road_address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    lawd_cd: Mapped[str | None] = mapped_column(String(5), index=True, nullable=True)
    dong_name: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    tuition: Mapped[int | None] = mapped_column(Integer, nullable=True)           # 공개 수강료/사용료(원). 없으면 null
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)         # 운영/등록 상태(개설/휴원/폐업 등)
    attrs: Mapped[dict | None] = mapped_column(JSON, nullable=True)               # 소스별 부가(운영시간·정원·연락처·면적 등)
    # --- 출처/등록 구분(현재 public만, 등록·광고 자리 미리) ---
    source: Mapped[str] = mapped_column(String(12), default="public", index=True)  # public/claimed/ad
    source_dataset: Mapped[str | None] = mapped_column(String(40), nullable=True)  # 원천 데이터셋 식별(gov_academy 등)
    source_key: Mapped[str] = mapped_column(String(160), unique=True)             # 원천 고유키(중복 적재 방지)
    claimed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)        # 향후 업체 계정 id(등록 시)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_places_cat_lawd", "category", "lawd_cd"),
        Index("ix_places_subcat_lawd", "subcategory", "lawd_cd"),
        # 부하 감사 M4: 단지상세·지도 bbox(lat/lng between) 조회가 풀스캔이던 것
        Index("ix_places_lat_lng", "lat", "lng"),
    )


class Landmark(Base):
    """개발 호재/이슈(청주 하이퍼로컬) — 위치 + 사실 + 출처.

    왜곡 없음 원칙(중요):
      - status 로 단계를 명확히(confirmed 확정 / ongoing 추진 / planned 계획).
      - summary 는 '사실'만(예: "2029년 준공 목표, 1.16조원"). 집값 상승 단정·투자 권유 금지.
      - source_name/url 필수(출처 없는 호재 등록 금지).
    향후 자동수집/큐레이션 교체 대비 source 계열 필드 보유(현재는 수동 큐레이션 전제).
    """
    __tablename__ = "landmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(16), index=True)   # industry/transport/commercial/residential/public
    status: Mapped[str] = mapped_column(String(12), index=True)     # confirmed/ongoing/planned
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str | None] = mapped_column(String(400), nullable=True)   # 사실만
    expected_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(120), nullable=True)  # 출처(필수 권장)
    source_url: Mapped[str | None] = mapped_column(String(400), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GuideSeries(Base):
    """집사 도감 — 시리즈(카테고리). 예: '집사가 알려주는 청주'.
    콘텐츠는 관리자 큐레이션(주 1편 페이스). 왜곡 없음: 편 본문은 사실+근거만."""
    __tablename__ = "guide_series"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)   # 'cheongju' 등
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    cover_emoji: Mapped[str | None] = mapped_column(String(8), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class Guide(Base):
    """집사 도감 — 편(글). 본문은 마크다운.
    발행 워크플로: admin 작성(is_published=False 초안 가능) → 검수 → 발행."""
    __tablename__ = "guides"
    __table_args__ = (Index("ix_guides_series_pub", "series_key", "is_published"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_key: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(160))
    body_md: Mapped[str] = mapped_column(Text)                        # 마크다운 원문
    cover_emoji: Mapped[str | None] = mapped_column(String(8), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
                                                 onupdate=datetime.utcnow)
