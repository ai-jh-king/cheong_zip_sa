"""경매·공매 — 온비드 tolerant 매핑·미연동 안내(왜곡 없음)."""
from app.sources.onbid import normalize_item, _rows_from_xml


def test_normalize_tolerant():
    r = normalize_item({"CLTR_NM": "청주시 흥덕구 가경동 아파트", "LDNM_ADRS": "충북 청주시 흥덕구 가경동 1",
                        "MIN_BID_PRC": "123,000,000", "APSL_ASES_AVG_AMT": "150000000",
                        "PBCT_CLS_DTM": "2026-08-01 17:00", "CTGR_FULL_NM": "부동산/주거용"})
    assert r["min_bid"] == 123000000 and r["appraisal"] == 150000000
    assert r["addr"].startswith("충북 청주시")
    r2 = normalize_item({})                      # 필드 전무 → 전부 None(추측 금지)
    assert r2["name"] is None and r2["min_bid"] is None


def test_rows_from_xml():
    xml = ("<response><body><items>"
           "<item><CLTR_NM>물건A</CLTR_NM><MIN_BID_PRC>1000</MIN_BID_PRC></item>"
           "<item><CLTR_NM>물건B</CLTR_NM></item>"
           "</items></body></response>")
    rows = _rows_from_xml(xml)
    assert len(rows) == 2 and rows[0]["CLTR_NM"] == "물건A"
    assert _rows_from_xml("깨진<xml") == []


def test_public_sale_api_disconnected(client, db, monkeypatch):
    # 키 없음 → connected false + 링크·면책은 항상 제공
    from app.core import config
    monkeypatch.setattr(config.get_settings(), "molit_service_key", "", raising=False)
    monkeypatch.setattr(config.get_settings(), "onbid_api_key", "", raising=False)
    j = client.get("/auction/public-sale").json()
    assert j["items"] == [] or isinstance(j["items"], list)
    assert j["links"] and j["disclaimer"]
