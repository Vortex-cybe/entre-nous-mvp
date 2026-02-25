from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse
from starlette.requests import Request

from app.core.settings import settings
from app.core.logging import configure_logging, log
from app.core.middleware import SecurityHeadersMiddleware, IPBanMiddleware, MetricsMiddleware
from app.api import auth, posts, feed, moderation, gdpr, admin, dm

configure_logging()

# IMPORTANT: for anonymity, avoid persisting IPs. Rate-limit uses remote address in-memory/redis only.
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Entre Nous MVP API", version="0.1.0")
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(IPBanMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(feed.router)
app.include_router(moderation.router)
app.include_router(gdpr.router)
app.include_router(admin.router)
app.include_router(dm.router)

@app.get("/health")
@limiter.limit("30/minute")
async def health(request: Request):
    return {"ok": True}
