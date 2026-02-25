from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timezone
import statistics

from app.db.session import get_db
from app.core.settings import settings
from app.core.redis import get_redis
from app.models import ModerationQueueItem, ModerationFlag, IpBan, Post, Reply

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(token: str | None):
    if not token or token != settings.admin_ui_token:
        raise HTTPException(status_code=403, detail="Forbidden")

@router.get("/overview")
async def overview(x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)):
    require_admin(x_admin_token)
    # counts
    pending = (await db.execute(select(ModerationQueueItem).where(ModerationQueueItem.status == "pending"))).scalars().all()
    last_flags = (await db.execute(select(ModerationFlag).order_by(desc(ModerationFlag.created_at)).limit(50))).scalars().all()
    bans = (await db.execute(select(IpBan).order_by(desc(IpBan.created_at)).limit(100))).scalars().all()

    # latency stats from redis
    r = get_redis()
    samples = r.lrange("metrics:latency_ms:last500", 0, 499) or []
    vals = [float(x) for x in samples if x]
    p50 = statistics.median(vals) if vals else None
    p95 = statistics.quantiles(vals, n=20)[-1] if len(vals) >= 40 else (max(vals) if vals else None)
    counts = r.hgetall("metrics:counts") or {}
    status = r.hgetall("metrics:status") or {}

    return {
        "metrics": {
            "latency_ms_p50": p50,
            "latency_ms_p95": p95,
            "requests_total": int(counts.get("requests", 0)),
            "status_counts": {k: int(v) for k, v in status.items()},
        },
        "moderation": {
            "pending_count": len(pending),
            "pending": [{"id": str(i.id), "target_type": i.target_type, "target_id": str(i.target_id), "priority": i.priority, "created_at": i.created_at} for i in pending[:50]],
            "last_flags": [{"id": str(f.id), "target_type": f.target_type, "target_id": str(f.target_id), "reason": f.reason, "created_at": f.created_at} for f in last_flags],
        },
        "bans": [{"id": str(b.id), "created_at": b.created_at, "reason": b.reason} for b in bans],
    }

@router.get("/content/{target_type}/{target_id}")
async def get_content(target_type: str, target_id: str, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)):
    require_admin(x_admin_token)
    # Only metadata; do not decrypt content here by default (reduce insider risk). Return status + flags.
    if target_type == "post":
        obj = (await db.execute(select(Post).where(Post.id == target_id))).scalar_one_or_none()
    else:
        obj = (await db.execute(select(Reply).where(Reply.id == target_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    return {"id": str(obj.id), "status": obj.status, "flags_count": obj.flags_count, "created_at": obj.created_at}

