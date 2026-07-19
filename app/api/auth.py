"""소셜 로그인(카카오·네이버) + 세션 토큰.

- 키가 설정되면 실제 OAuth 동작(authorize→callback→token 교환→프로필→계정 upsert→세션 토큰).
- 키가 없으면 개발용 로그인(/auth/dev-login)으로 동작(운영 배포 시 AUTH_DEV_LOGIN=false 권장).
- 익명 device_id ↔ 계정 연결(DeviceLink)로 로그인 시 데이터 승격 기반 마련.
- 비밀키·토큰은 로그에 남기지 않는다.
"""
import secrets
from urllib.parse import quote as _urlquote

import httpx
from fastapi import APIRouter, Depends, Query, Header, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import make_token, read_token, sign_state, read_state
from app.db.session import get_db
from app.models import (Account, DeviceLink, Favorite, RecentView, SavedSearch,
                        UserPref, Post, Comment, PostLike, Bookmark, ReportLog,
                        Notification, PushSubscription, Listing, Inquiry)

router = APIRouter(prefix="/auth", tags=["auth"])


def owner_device_ids(db: Session, device_id: str | None, authorization: str | None) -> list[str]:
    """현재 요청의 '소유 device_id 집합'.
    로그인 상태면 계정에 연결된 모든 device를 합쳐 cross-device로 데이터를 묶는다.
    비로그인이면 현재 device 하나만."""
    ids: set[str] = set()
    if device_id:
        ids.add(device_id)
    acc = account_from_auth(db, authorization)
    if acc:
        linked = db.scalars(select(DeviceLink.device_id)
                            .where(DeviceLink.account_id == acc.id)).all()
        ids.update([d for d in linked if d])
    return list(ids)


def _adopt_device_data(db: Session, acc: Account) -> None:
    """로그인 시 익명 device의 매물을 계정으로 흡수(account_id 부여).
    관심·검색·최근은 device 연결(DeviceLink) 기반 union으로 자동 통합되므로 별도 이관 불필요."""
    from app.models import Listing
    dids = db.scalars(select(DeviceLink.device_id)
                      .where(DeviceLink.account_id == acc.id)).all()
    dids = [d for d in dids if d]
    if not dids:
        return
    db.execute(update(Listing).where(Listing.device_id.in_(dids),
                                     Listing.account_id.is_(None))
               .values(account_id=acc.id))
    db.commit()


def _redirect_uri(s, provider: str) -> str:
    base = (s.auth_redirect_base or "").rstrip("/")
    return f"{base}/auth/callback/{provider}"


def _acc(a: Account) -> dict:
    from app.services.entitlement import is_premium
    return {"id": a.id, "role": a.role, "nickname": a.nickname, "provider": a.provider,
            "plan": getattr(a, "plan", "free"), "is_premium": is_premium(a)}


def _upsert_account(db: Session, provider: str, uid: str, nick: str | None) -> Account:
    acc = db.scalar(select(Account).where(Account.provider == provider,
                                          Account.provider_uid == uid))
    if not acc:
        acc = Account(provider=provider, provider_uid=uid, role="user", nickname=nick or None)
        db.add(acc)
        db.commit()
        db.refresh(acc)
    elif nick and acc.nickname != nick:
        acc.nickname = nick
        db.commit()
    return acc


def _link_device(db: Session, device_id: str, account_id: int) -> None:
    if not device_id:
        return
    link = db.get(DeviceLink, device_id)
    if link:
        link.account_id = account_id
    else:
        db.add(DeviceLink(device_id=device_id, account_id=account_id))
    db.commit()


def account_from_auth(db: Session, authorization: str | None) -> Account | None:
    """Bearer 토큰 → 계정. 다른 라우터(매물 등)에서 재사용."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    payload = read_token(authorization.split(" ", 1)[1])
    if not payload:
        return None
    try:
        return db.get(Account, int(payload["sub"]))
    except Exception:
        return None


def _exchange_and_profile(s, provider: str, code: str, state: str):
    """code → access_token → 프로필(provider_uid, nickname). 실패 시 상세 예외를 남긴다."""
    if provider == "kakao":
        data = {"grant_type": "authorization_code", "client_id": s.kakao_login_rest_key,
                "redirect_uri": _redirect_uri(s, "kakao"), "code": code}
        # 카카오 콘솔 '보안'에서 Client Secret 사용을 켠 앱은 필수. 안 켰으면 무시됨(있어도 무해).
        if getattr(s, "kakao_login_client_secret", ""):
            data["client_secret"] = s.kakao_login_client_secret
        tok = httpx.post(s.kakao_token_url, data=data, timeout=10).json()
        at = tok.get("access_token")
        if not at:
            raise RuntimeError(f"kakao token 실패: {tok.get('error') or tok.get('msg') or tok}")
        me = httpx.get(s.kakao_userinfo_url,
                       headers={"Authorization": f"Bearer {at}"}, timeout=10).json()
        uid = str(me.get("id") or "")
        if not uid:
            raise RuntimeError(f"kakao profile 실패: {me.get('msg') or me}")
        nick = ((me.get("kakao_account", {}) or {}).get("profile", {}) or {}).get("nickname") \
            or (me.get("properties", {}) or {}).get("nickname")
        return uid, nick
    tok = httpx.post(s.naver_token_url, data={
        "grant_type": "authorization_code", "client_id": s.naver_login_client_id,
        "client_secret": s.naver_login_client_secret, "code": code, "state": state,
    }, timeout=10).json()
    at = tok.get("access_token")
    if not at:
        raise RuntimeError(f"naver token 실패: {tok.get('error') or tok.get('error_description') or tok}")
    me = httpx.get(s.naver_userinfo_url,
                   headers={"Authorization": f"Bearer {at}"}, timeout=10).json()
    r = me.get("response", {}) or {}
    uid = str(r.get("id") or "")
    if not uid:
        raise RuntimeError(f"naver profile 실패: {me.get('message') or me}")
    return uid, (r.get("nickname") or r.get("name"))


@router.get("/config")
def auth_config():
    s = get_settings()
    kakao = bool(s.kakao_login_rest_key)
    naver = bool(s.naver_login_client_id and s.naver_login_client_secret)
    return {
        "providers": {"kakao": kakao, "naver": naver},
        "dev_login": bool(s.auth_dev_login),
        "enabled": kakao or naver or bool(s.auth_dev_login),
        "redirect_configured": bool(s.auth_redirect_base),
        "note": "키 설정 시 실제 소셜 로그인, 미설정 시 개발용 로그인으로 동작합니다.",
    }


@router.get("/login/{provider}")
def login_url(provider: str, device_id: str = Query("")):
    s = get_settings()
    if provider not in ("kakao", "naver"):
        raise HTTPException(status_code=404, detail="지원하지 않는 provider")
    if not s.auth_redirect_base:
        raise HTTPException(status_code=400, detail="AUTH_REDIRECT_BASE(배포 도메인) 설정이 필요합니다.")
    state = sign_state(f"{device_id}|{secrets.token_urlsafe(8)}")
    ru = _urlquote(_redirect_uri(s, provider), safe="")   # https://... → https%3A%2F%2F... (콘솔 등록값과 완전 일치 필수)
    st = _urlquote(state, safe="")
    if provider == "kakao":
        if not s.kakao_login_rest_key:
            raise HTTPException(status_code=400, detail="카카오 로그인 키 미설정")
        url = (f"{s.kakao_authorize_url}?response_type=code"
               f"&client_id={s.kakao_login_rest_key}&redirect_uri={ru}&state={st}")
    else:
        if not (s.naver_login_client_id and s.naver_login_client_secret):
            raise HTTPException(status_code=400, detail="네이버 로그인 키 미설정")
        url = (f"{s.naver_authorize_url}?response_type=code"
               f"&client_id={s.naver_login_client_id}&redirect_uri={ru}&state={st}")
    return {"url": url}


@router.get("/callback/{provider}")
def callback(provider: str, code: str = Query(""), state: str = Query(""),
             db: Session = Depends(get_db)):
    s = get_settings()
    app_base = (s.auth_redirect_base or "").rstrip("/")
    data = read_state(state)
    if not code or data is None:
        return RedirectResponse(f"{app_base}/?login=error")
    device_id = data.split("|")[0] if data else ""
    try:
        uid, nick = _exchange_and_profile(s, provider, code, state)
    except Exception as e:
        import logging
        logging.getLogger("auth.oauth").exception("%s 콜백 실패: %s", provider, e)
        # URL 에 사유 힌트(내용은 짧게, 시크릿 노출 없음)
        from urllib.parse import quote as _q
        reason = _q(str(e)[:120], safe="")
        return RedirectResponse(f"{app_base}/?login=error&provider={provider}&why={reason}")
    if not uid:
        return RedirectResponse(f"{app_base}/?login=error")
    acc = _upsert_account(db, provider, uid, nick)
    _link_device(db, device_id, acc.id)
    _adopt_device_data(db, acc)
    token = make_token(acc.id, acc.role, acc.nickname, provider)
    return RedirectResponse(f"{app_base}/?login=ok#token={token}")


class DevLoginIn(BaseModel):
    device_id: str
    nickname: str | None = None
    role: str | None = None


@router.post("/dev-login")
def dev_login(body: DevLoginIn, db: Session = Depends(get_db)):
    s = get_settings()
    if not s.auth_dev_login:
        raise HTTPException(status_code=403, detail="개발용 로그인이 비활성화되어 있습니다.")
    uid = "dev_" + (body.device_id or secrets.token_urlsafe(6))
    acc = _upsert_account(db, "dev", uid, body.nickname or "테스트 사용자")
    if body.role in ("user", "agent") and acc.role != body.role:
        acc.role = body.role
        db.commit()
    _link_device(db, body.device_id, acc.id)
    _adopt_device_data(db, acc)
    token = make_token(acc.id, acc.role, acc.nickname, "dev")
    return {"token": token, "account": _acc(acc)}


@router.get("/me")
def me(db: Session = Depends(get_db), authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    if not acc:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return {"account": _acc(acc)}


class RoleIn(BaseModel):
    role: str


@router.post("/role")
def set_role(body: RoleIn, db: Session = Depends(get_db),
             authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    if not acc:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    if body.role not in ("user", "agent"):
        raise HTTPException(status_code=422, detail="role은 user 또는 agent")
    acc.role = body.role
    db.commit()
    token = make_token(acc.id, acc.role, acc.nickname, acc.provider)
    return {"account": _acc(acc), "token": token}


@router.post("/logout")
def logout():
    return {"ok": True}


class DeleteMeIn(BaseModel):
    confirm: bool = False


@router.delete("/account")
def delete_account(body: DeleteMeIn, db: Session = Depends(get_db),
                   authorization: str | None = Header(None)):
    """회원 탈퇴 — 계정과 개인·행동 데이터를 영구 삭제(되돌릴 수 없음).

    설계(개인정보보호법·전자상거래법 고려):
    - **삭제**: 계정·기기연결·개인화(관심/최근/저장검색/설정)·좋아요/스크랩/신고·알림·푸시·내 매물·문의(받은+보낸).
    - **익명화**: 내 게시글/댓글(작성자 식별만 제거, 스레드는 보존).
    - **보존**: 구독/결제기록(전자상거래법 보존의무)·동의이력(처리 적법성 증빙) — 의도적 유지.
      (법무 판단에 따라 보존/삭제는 설정으로 조정 가능)
    원자적(한 트랜잭션 — 실패 시 전체 롤백). 확인(confirm=true) 필수.
    """
    acc = account_from_auth(db, authorization)
    if not acc:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    if not body.confirm:
        raise HTTPException(status_code=400, detail="탈퇴를 진행하려면 confirm=true 가 필요합니다.")

    aid = acc.id
    device_ids = [d.device_id for d in db.execute(
        select(DeviceLink).where(DeviceLink.account_id == aid)).scalars().all()]
    owners = [f"acct:{aid}"] + device_ids
    counts: dict[str, int] = {}

    def _del(model, cond, key):
        counts[key] = db.execute(delete(model).where(cond)).rowcount or 0

    # 개인화(기기 기준)
    if device_ids:
        _del(Favorite, Favorite.device_id.in_(device_ids), "favorites")
        _del(RecentView, RecentView.device_id.in_(device_ids), "recent")
        _del(SavedSearch, SavedSearch.device_id.in_(device_ids), "searches")
        _del(UserPref, UserPref.device_id.in_(device_ids), "prefs")
    else:
        counts.update(favorites=0, recent=0, searches=0, prefs=0)

    # 좋아요/스크랩/신고(owner 문자열: acct:<id> | device_id)
    _del(PostLike, PostLike.owner.in_(owners), "post_likes")
    _del(Bookmark, Bookmark.owner.in_(owners), "bookmarks")
    _del(ReportLog, ReportLog.owner.in_(owners), "reports")

    # 알림·푸시
    _del(Notification, Notification.account_id == aid, "notifications")
    push_cond = (PushSubscription.account_id == aid)
    if device_ids:
        push_cond = push_cond | PushSubscription.device_id.in_(device_ids)
    _del(PushSubscription, push_cond, "push")

    # 내 매물
    listing_cond = (Listing.account_id == aid)
    if device_ids:
        listing_cond = listing_cond | Listing.device_id.in_(device_ids)
    _del(Listing, listing_cond, "listings")

    # 문의(받은 + 보낸)
    inq_cond = (Inquiry.owner_account_id == aid)
    if device_ids:
        inq_cond = inq_cond | Inquiry.owner_device_id.in_(device_ids) \
            | Inquiry.inquirer_device_id.in_(device_ids)
    _del(Inquiry, inq_cond, "inquiries")

    # 게시글/댓글 익명화(스레드 보존)
    anon = {"account_id": None, "device_id": None, "nickname": "(탈퇴한 사용자)"}
    post_cond = (Post.account_id == aid)
    com_cond = (Comment.account_id == aid)
    if device_ids:
        post_cond = post_cond | Post.device_id.in_(device_ids)
        com_cond = com_cond | Comment.device_id.in_(device_ids)
    counts["posts_anon"] = db.execute(update(Post).where(post_cond).values(**anon)).rowcount or 0
    counts["comments_anon"] = db.execute(update(Comment).where(com_cond).values(**anon)).rowcount or 0

    # 기기연결·계정 삭제
    _del(DeviceLink, DeviceLink.account_id == aid, "device_links")
    db.delete(acc)

    db.commit()
    return {"ok": True, "deleted": counts,
            "retained": {"subscriptions": "전자상거래법 보존의무", "consents": "동의 증빙"}}
