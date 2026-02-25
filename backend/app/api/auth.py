from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime, timezone

from app.db.session import get_db
from app.api.schemas import RegisterIn, LoginIn, TokenOut
from app.models import User, SessionEvent
from app.services.auth import hash_password, verify_password, create_access_token
from app.services.crypto import crypto

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=dict)
async def register(data: RegisterIn, request: Request, db: AsyncSession = Depends(get_db)):
    # No pseudo/username. Access key is email (stored encrypted + HMAC lookup).
    email_lookup = crypto.email_lookup(data.email)
    existing = await db.execute(select(User).where(User.email_lookup_hmac == email_lookup, User.deleted_at.is_(None)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Account already exists")
    ct, nonce = crypto.encrypt_text(data.email)
    client_ip = request.client.host if request.client else ""
    ip_key = crypto.ip_lookup(client_ip)
    ip_ct, ip_nonce = crypto.encrypt_text(client_ip)
    user = User(
        id=uuid4(),
        password_hash=hash_password(data.password),
        email_lookup_hmac=email_lookup,
        email_ciphertext=ct,
        email_nonce=nonce,
        last_ip_lookup_hmac=ip_key,
        last_ip_ciphertext=ip_ct,
        last_ip_nonce=ip_nonce,
        created_at=datetime.now(timezone.utc),
        trust_score=0.0,
        is_banned=False,
    )
    db.add(user)
    db.add(SessionEvent(id=uuid4(), user_id=user.id, event_type="register", ip_lookup_hmac=ip_key, ip_ciphertext=ip_ct, ip_nonce=ip_nonce, created_at=datetime.now(timezone.utc)))
    await db.commit()
    return {"ok": True}

@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    email_lookup = crypto.email_lookup(data.email)
    res = await db.execute(select(User).where(User.email_lookup_hmac == email_lookup, User.deleted_at.is_(None)))
    user = res.scalar_one_or_none()
    if not user or user.is_banned:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    client_ip = request.client.host if request.client else ""
    ip_key = crypto.ip_lookup(client_ip)
    ip_ct, ip_nonce = crypto.encrypt_text(client_ip)
    user.last_ip_lookup_hmac = ip_key
    user.last_ip_ciphertext = ip_ct
    user.last_ip_nonce = ip_nonce
    db.add(SessionEvent(id=uuid4(), user_id=user.id, event_type="login", ip_lookup_hmac=ip_key, ip_ciphertext=ip_ct, ip_nonce=ip_nonce, created_at=datetime.now(timezone.utc)))
    await db.commit()
    token = create_access_token(str(user.id))
    return TokenOut(access_token=token)


