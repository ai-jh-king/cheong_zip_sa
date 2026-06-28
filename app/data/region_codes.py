"""
청주시 4개 행정구 법정동 코드 (실거래가 API 의 '지역코드' = 법정동코드 앞 5자리).

⚠️ 지침서 3.4: 아래 값은 '검증 대상'이다. 코드가 틀리면 데이터가 통째로 비므로,
   실제 API 응답으로 반드시 확인할 것 (scripts/verify_region_codes.py).
   하드코딩 금지 원칙에 따라 '지역 추가/수정은 이 표만 고치면' 되도록 분리.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class District:
    code: str          # 법정동코드 앞 5자리 (LAWD_CD)
    name: str          # 구 이름
    verified: bool     # 실제 API 응답으로 검증되었는지 여부


# 충북 청주시 (확인 전 잠정값 — verified=False)
CHEONGJU_DISTRICTS: list[District] = [
    District(code="43111", name="상당구", verified=False),
    District(code="43112", name="서원구", verified=False),
    District(code="43113", name="흥덕구", verified=False),
    District(code="43114", name="청원구", verified=False),
]

# 확장 대비: 충북 전역 등 신규 지역은 위 리스트에 항목만 추가하면 됨 (부록 B-3).

DISTRICT_BY_CODE = {d.code: d for d in CHEONGJU_DISTRICTS}

# 구(區) 대표 좌표 — 지도 '구 단위' 집계 마커용(근사 중심점).
# ⚠️ 단지별 정밀 위치가 아니라 '구 평균'을 표시하기 위한 대표점이다(왜곡 방지 위해 UI에 '구 평균'으로 명시).
#    단지별 정확한 핀은 지오코딩(scripts.geocode) 결과(Complex.lat/lng)로 표시된다.
DISTRICT_CENTROIDS: dict[str, tuple[float, float]] = {
    "43111": (36.6285, 127.5060),  # 상당구(동부: 용암·금천·성안)
    "43112": (36.6005, 127.4760),  # 서원구(남부: 분평·산남·사창)
    "43113": (36.6360, 127.4280),  # 흥덕구(서부: 복대·가경·봉명)
    "43114": (36.6720, 127.4880),  # 청원구(북부: 율량·내덕·오창 방면)
}


def all_codes() -> list[str]:
    return [d.code for d in CHEONGJU_DISTRICTS]
