from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Content-Security-Policy should be tuned per deployment / frontend hosting
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.services.crypto import crypto
from app.models import IpBan

class IPBanMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Compute privacy-friendly lookup (prefix-based) and block if banned.
        client_host = request.client.host if request.client else ""
        ip_key = crypto.ip_lookup(client_host)
        async with AsyncSessionLocal() as db:  # short-lived session for ban check
            res = await db.execute(select(IpBan.id).where(IpBan.ip_lookup_hmac == ip_key))
            if res.scalar_one_or_none():
                return Response(status_code=403, content="Forbidden")
        return await call_next(request)

import time
from app.core.redis import get_redis

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response: Response = await call_next(request)
        ms = (time.perf_counter() - start) * 1000.0
        try:
            r = get_redis()
            key = "metrics:latency_ms:last500"
            r.lpush(key, f"{ms:.3f}")
            r.ltrim(key, 0, 499)
            r.hincrby("metrics:counts", "requests", 1)
            r.hincrby("metrics:status", str(response.status_code), 1)
        except Exception:
            # metrics must never break the API
            pass
        response.headers["Server-Timing"] = f"app;dur={ms:.2f}"
        return response
