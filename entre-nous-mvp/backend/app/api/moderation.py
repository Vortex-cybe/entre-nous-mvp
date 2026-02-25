from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import uuid4, UUID
from datetime import datetime, timezone

from app.db.session import get_db
from app.api.deps import get_current_user
from app.api.schemas import FlagIn
from app.models import User, Post, Reply, ModerationFlag, ModerationQueueItem, IpBan, SessionEvent
from app.core.settings import settings

router = APIRouter(prefix="/moderation", tags=["moderation"])

AUTO_HIDE_FLAGS = 3

@router.post("/flag")
async def flag_item(data: FlagIn, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    flag = ModerationFlag(
        id=uuid4(),
        reporter_id=user.id,
        target_type=data.target_type,
        target_id=data.target_id,
        reason=data.reason,
        details=data.details,
        created_at=datetime.now(timezone.utc),
    )
    db.add(flag)

    if data.target_type == "post":
        await db.execute(update(Post).where(Post.id == data.target_id).values(flags_count=Post.flags_count + 1))
        res = await db.execute(select(Post.flags_count).where(Post.id == data.target_id))
        fc = res.scalar_one_or_none()
        if fc is not None and fc + 1 >= AUTO_HIDE_FLAGS:
            await db.execute(update(Post).where(Post.id == data.target_id).values(status="hidden"))
            db.add(ModerationQueueItem(
                id=uuid4(), target_type="post", target_id=data.target_id,
                priority=1, status="pending", created_at=datetime.now(timezone.utc)
            ))
    else:
        await db.execute(update(Reply).where(Reply.id == data.target_id).values(flags_count=Reply.flags_count + 1))
        res = await db.execute(select(Reply.flags_count).where(Reply.id == data.target_id))
        fc = res.scalar_one_or_none()
        if fc is not None and fc + 1 >= AUTO_HIDE_FLAGS:
            await db.execute(update(Reply).where(Reply.id == data.target_id).values(status="hidden"))
            db.add(ModerationQueueItem(
                id=uuid4(), target_type="reply", target_id=data.target_id,
                priority=1, status="pending", created_at=datetime.now(timezone.utc)
            ))

    client_ip = request.client.host if request.client else ""
    ip_key = crypto.ip_lookup(client_ip)
    ip_ct, ip_nonce = crypto.encrypt_text(client_ip)
    db.add(SessionEvent(id=uuid4(), user_id=user.id, event_type="flag", ip_lookup_hmac=ip_key, ip_ciphertext=ip_ct, ip_nonce=ip_nonce, created_at=datetime.now(timezone.utc)))
    await db.commit()
    return {"ok": True}

def _require_admin(token: str | None):
    if not token or token != settings.admin_review_token:
        raise HTTPException(status_code=403, detail="Forbidden")

@router.get("/queue")
async def queue(x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_admin_token)
    res = await db.execute(
        select(ModerationQueueItem)
        .where(ModerationQueueItem.status == "pending")
        .order_by(ModerationQueueItem.priority.asc(), ModerationQueueItem.created_at.asc())
        .limit(200)
    )
    return [{"id": str(i.id), "target_type": i.target_type, "target_id": str(i.target_id), "priority": i.priority, "created_at": i.created_at} for i in res.scalars().all()]

@router.post("/queue/{item_id}/decision")
async def decide(item_id: UUID, decision: str, notes: str | None = None, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_admin_token)
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="decision must be approve|reject")

    res = await db.execute(select(ModerationQueueItem).where(ModerationQueueItem.id == item_id))
    item = res.scalar_one_or_none()
    if not item or item.status != "pending":
        raise HTTPException(status_code=404, detail="Queue item not found")

    # Apply decision to target
    if item.target_type == "post":
        await db.execute(update(Post).where(Post.id == item.target_id).values(status="visible" if decision=="approve" else "removed"))
    else:
        await db.execute(update(Reply).where(Reply.id == item.target_id).values(status="visible" if decision=="approve" else "removed"))

    await db.execute(update(ModerationQueueItem).where(ModerationQueueItem.id == item_id).values(
        status="approved" if decision=="approve" else "rejected",
        notes=notes,
        decided_at=datetime.now(timezone.utc),
    ))
    await db.commit()
    return {"ok": True}

@router.post("/ban/ip")
async def ban_ip(ip: str, reason: str | None = None, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_admin_token)
    ip_key = crypto.ip_lookup(ip)
    # upsert-ish
    existing = await db.execute(select(IpBan).where(IpBan.ip_lookup_hmac == ip_key))
    if existing.scalar_one_or_none():
        return {"ok": True, "already": True}
    ct, nonce = crypto.encrypt_text(ip)
    ban = IpBan(
        id=uuid4(),
        ip_lookup_hmac=ip_key,
        ip_ciphertext=ct,
        ip_nonce=nonce,
        reason=reason,
        created_at=datetime.now(timezone.utc),
    )
    db.add(ban)
    await db.commit()
    return {"ok": True}
