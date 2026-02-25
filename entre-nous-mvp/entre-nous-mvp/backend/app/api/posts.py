from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.db.session import get_db
from app.api.deps import get_current_user
from app.api.schemas import PostCreateIn, ReplyCreateIn, PostOut, ReplyOut
from app.models import User, Post, Reply, ModerationQueueItem, SessionEvent
from app.services.crypto import crypto
from app.services.moderation import quick_moderation

router = APIRouter(tags=["content"])

@router.post("/posts", response_model=PostOut)
async def create_post(data: PostCreateIn, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    mod = quick_moderation(data.body)
    if not mod.allow:
        raise HTTPException(status_code=400, detail={"blocked": mod.reasons})
    ct, nonce = crypto.encrypt_text(data.body)
    post = Post(
        id=uuid4(),
        author_id=user.id,
        body_ciphertext=ct,
        body_nonce=nonce,
        created_at=datetime.now(timezone.utc),
        status="visible",
        toxicity_score=mod.risk,
        flags_count=0,
    )
    db.add(post)
    # If risk high enough, enqueue for human review (layer 3)
    if mod.risk >= 0.6:
        q = ModerationQueueItem(
            id=uuid4(),
            target_type="post",
            target_id=post.id,
            priority=3,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(q)
    client_ip = request.client.host if request.client else ""
    ip_key = crypto.ip_lookup(client_ip)
    ip_ct, ip_nonce = crypto.encrypt_text(client_ip)
    db.add(SessionEvent(id=uuid4(), user_id=user.id, event_type="post", ip_lookup_hmac=ip_key, ip_ciphertext=ip_ct, ip_nonce=ip_nonce, created_at=datetime.now(timezone.utc)))
    await db.commit()
    return PostOut(id=post.id, body=data.body, created_at=post.created_at, flags_count=0)

@router.post("/posts/{post_id}/reply", response_model=ReplyOut)
async def reply(post_id: UUID, data: ReplyCreateIn, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Post).where(Post.id == post_id, Post.status == "visible"))
    post = res.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    mod = quick_moderation(data.body)
    if not mod.allow:
        raise HTTPException(status_code=400, detail={"blocked": mod.reasons})
    ct, nonce = crypto.encrypt_text(data.body)
    reply = Reply(
        id=uuid4(),
        post_id=post.id,
        author_id=user.id,
        body_ciphertext=ct,
        body_nonce=nonce,
        created_at=datetime.now(timezone.utc),
        status="visible",
        toxicity_score=mod.risk,
        flags_count=0,
        kindness_votes=0,
    )
    db.add(reply)
    if mod.risk >= 0.6:
        q = ModerationQueueItem(
            id=uuid4(),
            target_type="reply",
            target_id=reply.id,
            priority=3,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(q)
    await db.commit()
    return ReplyOut(id=reply.id, post_id=reply.post_id, body=data.body, created_at=reply.created_at, flags_count=0, kindness_votes=0)

@router.post("/replies/{reply_id}/kindness")
async def vote_kindness(reply_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # One vote per user not implemented in MVP; add table reply_votes(user_id, reply_id) in v2.
    res = await db.execute(select(Reply).where(Reply.id == reply_id, Reply.status == "visible"))
    r = res.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Reply not found")
    await db.execute(update(Reply).where(Reply.id == reply_id).values(kindness_votes=Reply.kindness_votes + 1))
    # Simple trust bump for author (bounded)
    await db.execute(update(User).where(User.id == r.author_id).values(trust_score=User.trust_score + 0.02))
    await db.commit()
    return {"ok": True}
