from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
from typing import List

class Settings(BaseSettings):
    env: str = "dev"
    database_url: str
    redis_url: str

    jwt_secret: str
    jwt_issuer: str = "entre-nous"
    access_token_minutes: int = 30

    content_enc_key_b64: str
    admin_review_token: str
    admin_ui_token: str

    email_lookup_pepper: str
    ip_lookup_pepper: str

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
