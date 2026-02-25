from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from uuid import uuid4, UUID
from datetime import datetime, timezone

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models import User, Post, Conversation, ConversationParticipant, DMMessage, SessionEvent
from app.services.crypto import crypto
from pydantic import BaseModel, Field

router = APIRouter(prefix="/dm", tags=["dm"])

class DMStartFromPostIn(BaseModel):
    post_id: UUID

class DMSendIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

@router.post("/start_from_post")
async def start_from_post(data: DMStartFromPostIn, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    post = (await db.execute(select(Post).where(Post.id == data.post_id))).scalar_one_or_none()
    if not post or post.status != "visible":
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot DM yourself")

    # Find existing conversation between the two users by scanning participants (MVP). For scale, use deterministic pair table.
    conv_ids = (await db.execute(select(ConversationParticipant.conversation_id).where(ConversationParticipant.user_id == user.id))).scalars().all()
    if conv_ids:
        other = (await db.execute(
            select(ConversationParticipant.conversation_id)
            .where(ConversationParticipant.conversation_id.in_(conv_ids), ConversationParticipant.user_id == post.author_id)
        )).scalars().first()
        if other:
            return {"conversation_id": str(other)}

    conv = Conversation(id=uuid4(), created_at=datetime.now(timezone.utc))
    db.add(conv)
    db.add(ConversationParticipant(id=uuid4(), conversation_id=conv.id, user_id=user.id, created_at=datetime.now(timezone.utc)))
    db.add(ConversationParticipant(id=uuid4(), conversation_id=conv.id, user_id=post.author_id, created_at=datetime.now(timezone.utc)))

    # session event
    client_ip = request.client.host if request.client else ""
    ip_key = crypto.ip_lookup(client_ip)
    ip_ct, ip_nonce = crypto.encrypt_text(client_ip)
    db.add(SessionEvent(id=uuid4(), user_id=user.id, event_type="dm", ip_lookup_hmac=ip_key, ip_ciphertext=ip_ct, ip_nonce=ip_nonce, created_at=datetime.now(timezone.utc)))

    await db.commit()
    return {"conversation_id": str(conv.id)}

@router.get("/list")
async def list_conversations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Conversation.id, Conversation.created_at)
        .join(ConversationParticipant, ConversationParticipant.conversation_id == Conversation.id)
        .where(ConversationParticipant.user_id == user.id)
        .order_by(desc(Conversation.created_at))
        .limit(100)
    )
    return [{"conversation_id": str(cid), "created_at": created_at} for cid, created_at in res.all()]

@router.post("/{conversation_id}/send")
async def send(conversation_id: UUID, data: DMSendIn, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # membership check
    mem = (await db.execute(select(ConversationParticipant.id).where(ConversationParticipant.conversation_id == conversation_id, ConversationParticipant.user_id == user.id))).scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=403, detail="Forbidden")

    ct, nonce = crypto.encrypt_text(data.body)
    msg = DMMessage(id=uuid4(), conversation_id=conversation_id, author_id=user.id, body_ciphertext=ct, body_nonce=nonce, created_at=datetime.now(timezone.utc), status="visible")
    db.add(msg)

    # session event
    client_ip = request.client.host if request.client else ""
    ip_key = crypto.ip_lookup(client_ip)
    ip_ct, ip_nonce = crypto.encrypt_text(client_ip)
    db.add(SessionEvent(id=uuid4(), user_id=user.id, event_type="dm", ip_lookup_hmac=ip_key, ip_ciphertext=ip_ct, ip_nonce=ip_nonce, created_at=datetime.now(timezone.utc)))

    await db.commit()
    return {"ok": True, "message_id": str(msg.id)}

@router.get("/{conversation_id}/messages")
async def messages(conversation_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    mem = (await db.execute(select(ConversationParticipant.id).where(ConversationParticipant.conversation_id == conversation_id, ConversationParticipant.user_id == user.id))).scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=403, detail="Forbidden")

    res = await db.execute(select(DMMessage).where(DMMessage.conversation_id == conversation_id, DMMessage.status == "visible").order_by(desc(DMMessage.created_at)).limit(200))
    msgs = []
    for m in res.scalars().all():
        msgs.append({
            "id": str(m.id),
            "author_is_me": (m.author_id == user.id),
            "body": crypto.decrypt_text(m.body_ciphertext, m.body_nonce),
            "created_at": m.created_at,
        })
    msgs.reverse()
    return msgs
