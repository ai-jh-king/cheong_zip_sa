"""법적 고지 — 개인정보처리방침·이용약관 제공 + 동의 이력 기록(9.A).

- 문서는 app/web/legal/*.md 를 읽어 제공(버전 상수와 함께).
- 대출 민감정보 동의는 버전·시각을 Consent 에 기록한다(개인정보보호법 동의 이력).
- 라우트 순서 주의: 구체 경로(/version, /consent, /consent/status)를 catch-all /{doc} 보다 먼저 정의.
"""
from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Consent
from app.api.auth import account_from_auth

router = APIRouter(prefix="/legal", tags=["legal"])

# 정책 버전 — 문서 내용이 바뀌면 올린다(동의 이력이 이 버전에 묶임).
PRIVACY_VERSION = "2026-06-26"
TERMS_VERSION = "2026-06-19"
_DOCS = {"privacy": ("privacy.md", PRIVACY_VERSION), "terms": ("terms.md", TERMS_VERSION)}
_VERSION_BY_KIND = {"privacy_loan": PRIVACY_VERSION, "privacy": PRIVACY_VERSION, "terms": TERMS_VERSION}

LEGAL_DIR = Path(__file__).resolve().parents[1] / "web" / "legal"


def _owner(acc, device_id: str | None) -> str | None:
    if acc:
        return f"acct:{acc.id}"
    return device_id or None


def _read(filename: str) -> str:
    try:
        return (LEGAL_DIR / filename).read_text(encoding="utf-8")
    except OSError:
        return ""


@router.get("/version")
def versions():
    return {"privacy": PRIVACY_VERSION, "terms": TERMS_VERSION}


class ConsentIn(BaseModel):
    device_id: str | None = None
    kind: str = "privacy_loan"
    version: str | None = None


@router.post("/consent")
def record_consent(body: ConsentIn, db: Session = Depends(get_db),
                   authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    owner = _owner(acc, body.device_id)
    if not owner:
        raise HTTPException(400, "device_id 또는 로그인이 필요합니다.")
    version = body.version or _VERSION_BY_KIND.get(body.kind, PRIVACY_VERSION)
    db.add(Consent(owner=owner, kind=body.kind, policy_version=version))
    db.commit()
    return {"ok": True, "kind": body.kind, "version": version}


@router.get("/consent/status")
def consent_status(db: Session = Depends(get_db),
                   device_id: str | None = Query(None),
                   kind: str = Query("privacy_loan"),
                   authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    owner = _owner(acc, device_id)
    current = _VERSION_BY_KIND.get(kind, PRIVACY_VERSION)
    consented = False
    if owner:
        consented = db.scalar(
            select(Consent.id).where(
                Consent.owner == owner, Consent.kind == kind,
                Consent.policy_version == current).limit(1)) is not None
    return {"consented": consented, "version": current, "kind": kind}


@router.get("/{doc}")
def get_doc(doc: str):
    if doc not in _DOCS:
        raise HTTPException(404, "문서를 찾을 수 없습니다.")
    filename, version = _DOCS[doc]
    return {"doc": doc, "version": version, "content": _read(filename)}
