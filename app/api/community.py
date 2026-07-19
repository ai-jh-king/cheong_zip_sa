"""커뮤니티 게시판 — 부동산 소통(자유/질문/정보/매물상담/지역소식).

- 작성(글/댓글)은 로그인 필요. 좋아요/신고는 로그인 또는 익명(device) 모두 가능(중복 방지).
- 신고 임계치(REPORT_HIDE) 도달 시 자동 숨김(간이 자율 정화). 운영자 도구는 admin에서 확장 가능.
- ⚠️ 게시글은 사용자 의견으로 실거래·공식정보가 아님(프런트에 명시).
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, or_, update, case
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Post, Comment, PostLike, ReportLog, Notification, Bookmark
from app.api.auth import account_from_auth
from app.services.stats import _gu_name

router = APIRouter(prefix="/community", tags=["community"])
notif_router = APIRouter(prefix="/notifications", tags=["notifications"])

CATEGORIES = {"free": "자유", "qa": "질문답변", "info": "정보공유",
              "deal": "매물상담", "local": "지역소식"}
REPORT_HIDE = 5


def _notify(db, recipient_account_id, ntype, post_id, comment_id, actor_nick, message):
    """알림 생성. 수신자 없음/본인 알림은 생략. 커밋은 호출부에서."""
    if not recipient_account_id:
        return
    db.add(Notification(account_id=recipient_account_id, type=ntype, post_id=post_id,
                        comment_id=comment_id, actor_nickname=actor_nick, message=message))


def _owner(acc, device_id):
    return f"acct:{acc.id}" if acc else (device_id or "")


def _post_light(p: Post) -> dict:
    imgs = p.images or []
    return {"id": p.id, "category": p.category, "category_label": CATEGORIES.get(p.category, p.category),
            "title": p.title, "nickname": p.nickname or "회원", "account_id": p.account_id,
            "gu": _gu_name(p.lawd_cd) if p.lawd_cd else None, "lawd_cd": p.lawd_cd,
            "complex_name": p.complex_name, "property_type": p.property_type, "resident": bool(getattr(p, "resident", False)),
            "thumb": (imgs[0] if imgs else None), "image_count": len(imgs),
            "views": p.views, "like_count": p.like_count, "comment_count": p.comment_count,
            "is_sample": p.is_sample, "created_at": (p.created_at.isoformat() if p.created_at else None)}


def _post_full(p: Post) -> dict:
    d = _post_light(p)
    d["body"] = p.body
    d["images"] = p.images or []
    d["updated_at"] = p.updated_at.isoformat() if p.updated_at else None
    return d


def _comment(c: Comment) -> dict:
    return {"id": c.id, "parent_id": c.parent_id, "nickname": c.nickname or "회원",
            "account_id": c.account_id, "body": c.body, "is_sample": c.is_sample,
            "created_at": (c.created_at.isoformat() if c.created_at else None)}


class PostIn(BaseModel):
    device_id: str | None = None
    category: str = "free"
    title: str
    body: str
    lawd_cd: str | None = None
    complex_name: str | None = None
    property_type: str | None = None
    images: list | None = None


class CommentIn(BaseModel):
    device_id: str | None = None
    body: str
    parent_id: int | None = None


class ActionIn(BaseModel):
    device_id: str | None = None
    reason: str | None = None


def _my_home_of(db: Session, account_id: int) -> dict | None:
    """계정에 연결된 기기들의 UserPref에서 my_home(우리집)을 찾는다. 없으면 None."""
    from app.models import DeviceLink, UserPref
    ids = list(db.scalars(select(DeviceLink.device_id).where(DeviceLink.account_id == account_id)))
    if not ids:
        return None
    for row in db.scalars(select(UserPref).where(UserPref.device_id.in_(ids), UserPref.data.isnot(None))):
        mh = (row.data or {}).get("my_home")
        if isinstance(mh, dict) and mh.get("complex_name"):
            return mh
    return None


def _compute_resident(db: Session, account_id: int, complex_name: str | None,
                      lawd_cd: str | None) -> bool:
    """작성자의 '우리집(my_home)'과 글의 @단지 태그를 서버가 대조해 주민 여부를 산출.
    자가 신고가 아니라 '자가 등록 기반' 라벨(위조 불가). complex_name/lawd_cd 변경 시 반드시 재호출.
    (단지 태그 없으면 False. lawd_cd는 양쪽에 있을 때만 비교 — 없으면 단지명 일치로 인정.)"""
    if not complex_name:
        return False
    mh = _my_home_of(db, account_id)
    return bool(mh and mh.get("complex_name") == complex_name
                and (not lawd_cd or not mh.get("lawd_cd") or mh.get("lawd_cd") == lawd_cd))


@router.get("/categories")
def categories():
    return {"items": [{"key": k, "label": v} for k, v in CATEGORIES.items()]}


@router.get("/posts")
def list_posts(db: Session = Depends(get_db),
               category: str | None = Query(None),
               gu: str | None = Query(None),
               complex_name: str | None = Query(None, alias="complex"),
               q: str | None = Query(None),
               sort: str = Query("recent"),
               mine: bool = Query(False),
               page: int = Query(1, ge=1),
               per: int = Query(20, ge=1, le=50),
               authorization: str | None = Header(None)):
    qy = select(Post).where(Post.status == "active")
    if mine:
        acc = account_from_auth(db, authorization)
        if not acc:
            return {"items": [], "total": 0, "page": page, "per": per, "has_more": False}
        qy = qy.where(Post.account_id == acc.id)
    if category in CATEGORIES:
        qy = qy.where(Post.category == category)
    if gu:
        qy = qy.where(Post.lawd_cd == gu)
    if complex_name:
        qy = qy.where(Post.complex_name == complex_name)   # 단지 이야기(단지 상세 섹션)
    if q and q.strip():
        like = f"%{q.strip()}%"
        qy = qy.where(or_(Post.title.like(like), Post.body.like(like)))
    if sort == "popular":
        qy = qy.order_by((Post.like_count + Post.comment_count).desc(), Post.created_at.desc())
    else:
        qy = qy.order_by(Post.created_at.desc())
    total = db.scalar(select(func.count()).select_from(qy.subquery())) or 0
    rows = db.scalars(qy.limit(per).offset((page - 1) * per)).all()
    return {"items": [_post_light(p) for p in rows], "total": total,
            "page": page, "per": per, "has_more": page * per < total}


@router.get("/best")
def best_posts(db: Session = Depends(get_db), days: int = Query(7, ge=1, le=90),
               limit: int = Query(5, ge=1, le=20)):
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.scalars(
        select(Post).where(Post.status == "active", Post.created_at >= since,
                           (Post.like_count + Post.comment_count) > 0)
        .order_by((Post.like_count + Post.comment_count).desc(), Post.views.desc())
        .limit(limit)
    ).all()
    return {"items": [_post_light(p) for p in rows], "days": days}


@router.get("/mine")
def my_activity(db: Session = Depends(get_db), authorization: str | None = Header(None),
                limit: int = Query(30, ge=1, le=100)):
    acc = account_from_auth(db, authorization)
    if not acc:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    posts = db.scalars(select(Post).where(Post.account_id == acc.id, Post.status == "active")
                       .order_by(Post.created_at.desc()).limit(limit)).all()
    crows = db.scalars(select(Comment).where(Comment.account_id == acc.id, Comment.status == "active")
                       .order_by(Comment.created_at.desc()).limit(limit)).all()
    # 댓글에 글 제목 부착
    pids = {c.post_id for c in crows}
    titles = {p.id: p.title for p in db.scalars(select(Post).where(Post.id.in_(pids)))} if pids else {}
    comments = [{**_comment(c), "post_id": c.post_id, "post_title": titles.get(c.post_id)}
                for c in crows]
    return {"posts": [_post_light(p) for p in posts], "comments": comments}


@router.get("/posts/{pid}")
def get_post(pid: int, db: Session = Depends(get_db),
             device_id: str | None = Query(None),
             authorization: str | None = Header(None)):
    p = db.get(Post, pid)
    if not p or p.status != "active":
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    db.execute(update(Post).where(Post.id == pid)
               .values(views=func.coalesce(Post.views, 0) + 1))
    db.commit()
    db.refresh(p)
    comments = db.scalars(select(Comment).where(Comment.post_id == pid, Comment.status == "active")
                          .order_by(Comment.created_at.asc())).all()
    acc = account_from_auth(db, authorization)
    owner = _owner(acc, device_id)
    liked = bookmarked = False
    if owner:
        liked = db.scalar(select(PostLike.id).where(PostLike.post_id == pid, PostLike.owner == owner)) is not None
        bookmarked = db.scalar(select(Bookmark.id).where(Bookmark.post_id == pid, Bookmark.owner == owner)) is not None
    return {"post": _post_full(p), "comments": [_comment(c) for c in comments],
            "liked": liked, "bookmarked": bookmarked}


@router.post("/posts")
def create_post(body: PostIn, db: Session = Depends(get_db),
                authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    if not acc:
        raise HTTPException(status_code=401, detail="게시글 작성은 로그인이 필요합니다.")
    title = (body.title or "").strip()
    text = (body.body or "").strip()
    if not (2 <= len(title) <= 150):
        raise HTTPException(status_code=422, detail="제목은 2~150자로 입력하세요.")
    if len(text) < 2:
        raise HTTPException(status_code=422, detail="내용을 2자 이상 입력하세요.")
    cat = body.category if body.category in CATEGORIES else "free"
    imgs = [u for u in (body.images or []) if isinstance(u, str)][:8]
    p = Post(account_id=acc.id, device_id=body.device_id, nickname=acc.nickname or "회원",
             category=cat, title=title, body=text, lawd_cd=(body.lawd_cd or None),
             complex_name=(body.complex_name or None), property_type=(body.property_type or None),
             resident=_compute_resident(db, acc.id, body.complex_name, body.lawd_cd),
             images=(imgs or None), created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"ok": True, "post": _post_full(p)}


class PostEditIn(BaseModel):
    title: str | None = None
    body: str | None = None
    category: str | None = None
    lawd_cd: str | None = None
    complex_name: str | None = None
    property_type: str | None = None
    images: list | None = None


@router.put("/posts/{pid}")
def edit_post(pid: int, body: PostEditIn, db: Session = Depends(get_db),
              authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    p = db.get(Post, pid)
    if not p or p.status != "active":
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if not (acc and p.account_id == acc.id):
        raise HTTPException(status_code=403, detail="작성자만 수정할 수 있습니다.")
    if body.title is not None:
        t = body.title.strip()
        if not (2 <= len(t) <= 150):
            raise HTTPException(status_code=422, detail="제목은 2~150자로 입력하세요.")
        p.title = t
    if body.body is not None:
        bt = body.body.strip()
        if len(bt) < 2:
            raise HTTPException(status_code=422, detail="내용을 2자 이상 입력하세요.")
        p.body = bt
    if body.category in CATEGORIES:
        p.category = body.category
    if body.lawd_cd is not None:
        p.lawd_cd = body.lawd_cd or None
    if body.complex_name is not None:
        p.complex_name = body.complex_name or None
    if body.property_type is not None:
        p.property_type = body.property_type or None
    # @단지/지역 태그가 바뀌면 주민 뱃지를 서버가 재산출 — 다른 단지로 편집해 뱃지를 옮기는 위조를 차단.
    if body.complex_name is not None or body.lawd_cd is not None:
        p.resident = _compute_resident(db, p.account_id, p.complex_name, p.lawd_cd)
    if body.images is not None:
        p.images = [u for u in body.images if isinstance(u, str)][:8] or None
    p.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(p)
    return {"ok": True, "post": _post_full(p)}


@router.delete("/posts/{pid}")
def delete_post(pid: int, db: Session = Depends(get_db),
                authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    p = db.get(Post, pid)
    if not p:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if not (acc and p.account_id == acc.id):
        raise HTTPException(status_code=403, detail="작성자만 삭제할 수 있습니다.")
    p.status = "hidden"
    db.commit()
    return {"ok": True}


@router.post("/posts/{pid}/comments")
def add_comment(pid: int, body: CommentIn, db: Session = Depends(get_db),
                authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    if not acc:
        raise HTTPException(status_code=401, detail="댓글 작성은 로그인이 필요합니다.")
    p = db.get(Post, pid)
    if not p or p.status != "active":
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    text = (body.body or "").strip()
    if not (1 <= len(text) <= 2000):
        raise HTTPException(status_code=422, detail="댓글은 1~2000자로 입력하세요.")
    parent_id = None
    if body.parent_id:
        parent = db.get(Comment, body.parent_id)
        if parent and parent.post_id == pid and parent.status == "active":
            # 1단계로 평탄화: 답글의 답글은 최상위 부모로
            parent_id = parent.parent_id or parent.id
    c = Comment(post_id=pid, parent_id=parent_id, account_id=acc.id, device_id=body.device_id,
                nickname=acc.nickname or "회원", body=text, created_at=datetime.utcnow())
    db.add(c)
    db.flush()
    db.execute(update(Post).where(Post.id == pid)
               .values(comment_count=func.coalesce(Post.comment_count, 0) + 1))
    # 알림: 글 작성자 + (답글이면)부모 댓글 작성자. 본인 제외, 중복 제외.
    nick = acc.nickname or "회원"
    notified = {acc.id}
    snippet = (p.title or "")[:20]
    if p.account_id and p.account_id not in notified:
        _notify(db, p.account_id, "comment", pid, c.id, nick, f"{nick}님이 '{snippet}'에 댓글을 남겼어요")
        notified.add(p.account_id)
    if parent_id:
        pc = db.get(Comment, parent_id)
        if pc and pc.account_id and pc.account_id not in notified:
            _notify(db, pc.account_id, "reply", pid, c.id, nick, f"{nick}님이 회원님 댓글에 답글을 남겼어요")
    db.commit()
    db.refresh(c)
    return {"ok": True, "comment": _comment(c)}


class CommentEditIn(BaseModel):
    body: str


@router.put("/comments/{cid}")
def edit_comment(cid: int, body: CommentEditIn, db: Session = Depends(get_db),
                 authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    c = db.get(Comment, cid)
    if not c or c.status != "active":
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    if not (acc and c.account_id == acc.id):
        raise HTTPException(status_code=403, detail="작성자만 수정할 수 있습니다.")
    t = (body.body or "").strip()
    if not (1 <= len(t) <= 2000):
        raise HTTPException(status_code=422, detail="댓글은 1~2000자로 입력하세요.")
    c.body = t
    db.commit()
    return {"ok": True, "comment": _comment(c)}


@router.delete("/comments/{cid}")
def delete_comment(cid: int, db: Session = Depends(get_db),
                   authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    c = db.get(Comment, cid)
    if not c:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    if not (acc and c.account_id == acc.id):
        raise HTTPException(status_code=403, detail="작성자만 삭제할 수 있습니다.")
    c.status = "hidden"
    # 원자적 감소(경합 방지) — read-modify-write 금지. 0 미만으로 내려가지 않게 case 가드.
    db.execute(update(Post).where(Post.id == c.post_id)
               .values(comment_count=case(
                   (func.coalesce(Post.comment_count, 0) > 0, Post.comment_count - 1),
                   else_=0)))
    db.commit()
    return {"ok": True}


@router.post("/posts/{pid}/like")
def toggle_like(pid: int, body: ActionIn, db: Session = Depends(get_db),
                authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    owner = _owner(acc, body.device_id)
    if not owner:
        raise HTTPException(status_code=400, detail="device_id 또는 로그인이 필요합니다.")
    p = db.get(Post, pid)
    if not p or p.status != "active":
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    ex = db.scalar(select(PostLike).where(PostLike.post_id == pid, PostLike.owner == owner))
    if ex:
        db.delete(ex)
        db.execute(update(Post).where(Post.id == pid).values(
            like_count=case((func.coalesce(Post.like_count, 0) > 0, Post.like_count - 1), else_=0)))
        liked = False
    else:
        db.add(PostLike(post_id=pid, owner=owner))
        db.execute(update(Post).where(Post.id == pid)
                   .values(like_count=func.coalesce(Post.like_count, 0) + 1))
        liked = True
    db.commit()
    like_count = db.scalar(select(func.coalesce(Post.like_count, 0)).where(Post.id == pid)) or 0
    return {"liked": liked, "like_count": int(like_count)}


def _report(db, target_type, target_id, owner, reason):
    if not owner:
        raise HTTPException(status_code=400, detail="device_id 또는 로그인이 필요합니다.")
    obj = db.get(Post if target_type == "post" else Comment, target_id)
    if not obj or obj.status != "active":
        raise HTTPException(status_code=404, detail="대상을 찾을 수 없습니다.")
    dup = db.scalar(select(ReportLog).where(ReportLog.target_type == target_type,
                                            ReportLog.target_id == target_id,
                                            ReportLog.owner == owner))
    if dup:
        return {"ok": True, "duplicated": True, "report_count": obj.report_count}
    db.add(ReportLog(target_type=target_type, target_id=target_id, owner=owner, reason=reason))
    tbl = Post if target_type == "post" else Comment
    db.execute(update(tbl).where(tbl.id == target_id)
               .values(report_count=func.coalesce(tbl.report_count, 0) + 1))
    db.commit()
    new_count = db.scalar(select(func.coalesce(tbl.report_count, 0)).where(tbl.id == target_id)) or 0
    hidden = new_count >= REPORT_HIDE
    if hidden and obj.status == "active":
        db.execute(update(tbl).where(tbl.id == target_id).values(status="hidden"))
        db.commit()
    return {"ok": True, "report_count": int(new_count), "hidden": hidden}


@router.post("/posts/{pid}/report")
def report_post(pid: int, body: ActionIn, db: Session = Depends(get_db),
                authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    return _report(db, "post", pid, _owner(acc, body.device_id), body.reason)


@router.post("/comments/{cid}/report")
def report_comment(cid: int, body: ActionIn, db: Session = Depends(get_db),
                   authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    return _report(db, "comment", cid, _owner(acc, body.device_id), body.reason)


# ---------------- 스크랩(북마크) ----------------
@router.post("/posts/{pid}/bookmark")
def toggle_bookmark(pid: int, body: ActionIn, db: Session = Depends(get_db),
                    authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    owner = _owner(acc, body.device_id)
    if not owner:
        raise HTTPException(status_code=400, detail="device_id 또는 로그인이 필요합니다.")
    p = db.get(Post, pid)
    if not p or p.status != "active":
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    ex = db.scalar(select(Bookmark).where(Bookmark.post_id == pid, Bookmark.owner == owner))
    if ex:
        db.delete(ex)
        db.commit()
        return {"bookmarked": False}
    db.add(Bookmark(post_id=pid, owner=owner))
    db.commit()
    return {"bookmarked": True}


@router.get("/bookmarks")
def list_bookmarks(db: Session = Depends(get_db), device_id: str | None = Query(None),
                   authorization: str | None = Header(None), limit: int = Query(50, le=100)):
    acc = account_from_auth(db, authorization)
    owner = _owner(acc, device_id)
    if not owner:
        return {"items": []}
    pids = db.scalars(select(Bookmark.post_id).where(Bookmark.owner == owner)
                      .order_by(Bookmark.created_at.desc()).limit(limit)).all()
    if not pids:
        return {"items": []}
    posts = {p.id: p for p in db.scalars(select(Post).where(Post.id.in_(pids), Post.status == "active"))}
    items = [_post_light(posts[i]) for i in pids if i in posts]  # 스크랩 순서 유지
    return {"items": items}


# ---------------- 작성자 정보 ----------------
def _badge(post_count: int) -> str:
    if post_count >= 50:
        return "베테랑"
    if post_count >= 10:
        return "활발"
    if post_count >= 1:
        return "회원"
    return "새내기"


@router.get("/authors/{account_id}")
def author(account_id: int, db: Session = Depends(get_db), limit: int = Query(20, le=50)):
    posts = db.scalars(select(Post).where(Post.account_id == account_id, Post.status == "active")
                       .order_by(Post.created_at.desc()).limit(limit)).all()
    post_count = db.scalar(select(func.count()).select_from(Post)
                           .where(Post.account_id == account_id, Post.status == "active")) or 0
    like_total = db.scalar(select(func.coalesce(func.sum(Post.like_count), 0))
                           .where(Post.account_id == account_id, Post.status == "active")) or 0
    nickname = posts[0].nickname if posts else "회원"
    return {"account_id": account_id, "nickname": nickname, "post_count": int(post_count),
            "like_total": int(like_total), "badge": _badge(int(post_count)),
            "posts": [_post_light(p) for p in posts]}


# ---------------- 알림 ----------------
class ReadIn(BaseModel):
    ids: list[int] | None = None
    all: bool = False


@notif_router.get("")
def list_notifications(db: Session = Depends(get_db), authorization: str | None = Header(None),
                       limit: int = Query(30, le=100)):
    acc = account_from_auth(db, authorization)
    if not acc:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    rows = db.scalars(select(Notification).where(Notification.account_id == acc.id)
                      .order_by(Notification.created_at.desc()).limit(limit)).all()
    unread = db.scalar(select(func.count()).select_from(Notification)
                       .where(Notification.account_id == acc.id, Notification.is_read == False)) or 0  # noqa: E712
    items = [{"id": n.id, "type": n.type, "post_id": n.post_id, "comment_id": n.comment_id,
              "complex_name": n.complex_name, "lawd_cd": n.lawd_cd, "property_type": n.property_type,
              "actor_nickname": n.actor_nickname, "message": n.message, "is_read": n.is_read,
              "created_at": n.created_at.isoformat() if n.created_at else None} for n in rows]
    return {"items": items, "unread": int(unread)}


@notif_router.get("/unread_count")
def unread_count(db: Session = Depends(get_db), authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    if not acc:
        return {"unread": 0}
    unread = db.scalar(select(func.count()).select_from(Notification)
                       .where(Notification.account_id == acc.id, Notification.is_read == False)) or 0  # noqa: E712
    return {"unread": int(unread)}


@notif_router.post("/read")
def mark_read(body: ReadIn, db: Session = Depends(get_db), authorization: str | None = Header(None)):
    acc = account_from_auth(db, authorization)
    if not acc:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    from sqlalchemy import update
    q = update(Notification).where(Notification.account_id == acc.id)
    if not body.all and body.ids:
        q = q.where(Notification.id.in_(body.ids))
    elif not body.all and not body.ids:
        return {"ok": True}
    db.execute(q.values(is_read=True))
    db.commit()
    return {"ok": True}
