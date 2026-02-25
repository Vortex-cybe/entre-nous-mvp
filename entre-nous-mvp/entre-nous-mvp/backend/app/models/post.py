from __future__ import annotations
import uuid
from sqlalchemy import String, DateTime, ForeignKey, Float, Integer, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    body_ciphertext: Mapped[bytes] = mapped_column(LargeBinary(), nullable=False)
    body_nonce: Mapped[bytes] = mapped_column(LargeBinary(), nullable=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="visible")  # visible|hidden|removed
    toxicity_score: Mapped[float | None] = mapped_column(Float(), nullable=True)
    flags_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
