from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models import User, Post, Reply
from app.services.crypto import crypto

router = APIRouter(tags=["gdpr"])

@router.get("/me/export")
async def export_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    posts = (await db.execute(select(Post).where(Post.author_id == user.id))).scalars().all()
    replies = (await db.execute(select(Reply).where(Reply.author_id == user.id))).scalars().all()
    return {
        "user": {"id": str(user.id), "created_at": user.created_at, "trust_score": user.trust_score},
        "posts": [
            {"id": str(p.id), "created_at": p.created_at, "status": p.status, "body": crypto.decrypt_text(p.body_ciphertext, p.body_nonce)}
            for p in posts
        ],
        "replies": [
            {"id": str(r.id), "post_id": str(r.post_id), "created_at": r.created_at, "status": r.status, "body": crypto.decrypt_text(r.body_ciphertext, r.body_nonce)}
            for r in replies
        ],
    }

@router.delete("/me")
async def delete_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Soft delete user + remove their content from public surfaces.
    await db.execute(update(User).where(User.id == user.id).values(deleted_at=datetime.now(timezone.utc), is_banned=True))
    await db.execute(update(Post).where(Post.author_id == user.id).values(status="removed"))
    await db.execute(update(Reply).where(Reply.author_id == user.id).values(status="removed"))
    await db.commit()
    return {"ok": True}
