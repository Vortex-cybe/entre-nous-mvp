from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime

class RegisterIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)

class LoginIn(BaseModel):
    email: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class PostCreateIn(BaseModel):
    body: str = Field(min_length=2, max_length=2000)

class ReplyCreateIn(BaseModel):
    body: str = Field(min_length=2, max_length=2000)

class FlagIn(BaseModel):
    target_type: Literal["post", "reply", "dm"]
    target_id: UUID
    reason: str = Field(max_length=64)
    details: Optional[str] = Field(default=None, max_length=500)

class PostOut(BaseModel):
    id: UUID
    body: str
    created_at: datetime
    flags_count: int

class ReplyOut(BaseModel):
    id: UUID
    post_id: UUID
    body: str
    created_at: datetime
    flags_count: int
    kindness_votes: int

class FeedItem(BaseModel):
    post: PostOut
    score: float
