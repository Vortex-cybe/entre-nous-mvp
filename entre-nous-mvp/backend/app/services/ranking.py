from __future__ import annotations
from datetime import datetime, timezone
import math

def recency_boost(created_at: datetime) -> float:
    # Decays ~half every 12h
    age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600.0
    return 1.0 / (1.0 + (age_hours / 12.0))

def feed_score(trust_score: float, flags_count: int, created_at: datetime) -> float:
    # Boost benevolent users, penalize flags, keep recency.
    return (1.0 + max(0.0, trust_score)) * recency_boost(created_at) * (1.0 / (1.0 + flags_count))
