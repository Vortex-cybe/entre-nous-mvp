from __future__ import annotations

import uuid
from sqlalchemy import DateTime, String, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class SessionEvent(Base):
    __tablename__ = "session_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # login|register|post|reply|flag|dm
    ip_lookup_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_ciphertext: Mapped[bytes] = mapped_column(LargeBinary(), nullable=False)
    ip_nonce: Mapped[bytes] = mapped_column(LargeBinary(), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
