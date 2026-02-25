from __future__ import annotations
import uuid
from sqlalchemy import String, DateTime, Boolean, Float, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    email_lookup_hmac: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    email_ciphertext: Mapped[bytes] = mapped_column(LargeBinary(), nullable=False)
    email_nonce: Mapped[bytes] = mapped_column(LargeBinary(), nullable=False)

    last_ip_lookup_hmac: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_ip_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary(), nullable=True)
    last_ip_nonce: Mapped[bytes | None] = mapped_column(LargeBinary(), nullable=True)

    trust_score: Mapped[float] = mapped_column(Float(), nullable=False, default=0.0)
    is_banned: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
