from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Literal

TargetType = Literal["post", "reply"]

# MVP baseline: simple keyword screen + length checks.
# Replace with: embeddings + LLM policy model + language-specific classifiers.
PROFANITY = {"sale", "pute", "kill", "suicide", "self-harm", "hate"}

@dataclass
class ModerationResult:
    allow: bool
    risk: float
    reasons: list[str]

def quick_moderation(text: str) -> ModerationResult:
    reasons: list[str] = []
    t = text.strip()
    if len(t) < 2:
        return ModerationResult(False, 0.9, ["too_short"])
    if len(t) > 2000:
        return ModerationResult(False, 0.9, ["too_long"])
    lowered = re.sub(r"\s+", " ", t.lower())
    hits = [w for w in PROFANITY if w in lowered]
    if hits:
        # Don't block automatically; mark for review.
        reasons.append("keyword_hit")
        return ModerationResult(True, 0.65, reasons)
    return ModerationResult(True, 0.1, reasons)
