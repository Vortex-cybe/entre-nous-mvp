from __future__ import annotations
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.db.session import get_db
from app.services.auth import decode_token
from app.models import User

bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if cred is None:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = decode_token(cred.credentials)
        uid = UUID(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    res = await db.execute(select(User).where(User.id == uid, User.deleted_at.is_(None)))
    user = res.scalar_one_or_none()
    if not user or user.is_banned:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user
