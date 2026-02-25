from __future__ import annotations

import redis
from app.core.settings import settings

def get_redis() -> redis.Redis:
    # decode_responses False for bytes performance; we store small strings
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)
