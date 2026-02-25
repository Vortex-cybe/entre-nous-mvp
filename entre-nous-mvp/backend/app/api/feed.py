from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models import Post, User
from app.api.schemas import FeedItem, PostOut
from app.services.crypto import crypto
from app.services.ranking import feed_score

router = APIRouter(tags=["feed"])

@router.get("/feed", response_model=list[FeedItem])
async def get_feed(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    # Fetch recent visible posts; compute ranking using author trust score.
    res = await db.execute(
        select(Post, User.trust_score)
        .join(User, User.id == Post.author_id)
        .where(Post.status == "visible", User.deleted_at.is_(None), User.is_banned.is_(False))
        .order_by(desc(Post.created_at))
        .limit(100)
    )
    items = []
    for post, trust in res.all():
        body = crypto.decrypt_text(post.body_ciphertext, post.body_nonce)
        score = feed_score(trust, post.flags_count, post.created_at)
        items.append(FeedItem(post=PostOut(id=post.id, body=body, created_at=post.created_at, flags_count=post.flags_count), score=score))
    items.sort(key=lambda x: x.score, reverse=True)
    return items

from uuid import UUID
from app.models import Reply
from app.api.schemas import ReplyOut

@router.get("/posts/{post_id}/replies", response_model=list[ReplyOut])
async def get_replies(post_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    res = await db.execute(select(Reply).where(Reply.post_id == post_id, Reply.status == "visible").order_by(Reply.created_at.asc()).limit(200))
    out = []
    for r in res.scalars().all():
        body = crypto.decrypt_text(r.body_ciphertext, r.body_nonce)
        out.append(ReplyOut(id=r.id, post_id=r.post_id, body=body, created_at=r.created_at, flags_count=r.flags_count, kindness_votes=r.kindness_votes))
    return out
