from __future__ import annotations
import base64
from nacl.secret import SecretBox
from nacl.utils import random as nacl_random
from app.core.settings import settings
import hmac, hashlib

class ContentCrypto:
    def __init__(self) -> None:
        key = base64.b64decode(settings.content_enc_key_b64)
        if len(key) != SecretBox.KEY_SIZE:
            raise ValueError("CONTENT_ENC_KEY_B64 must decode to 32 bytes")
        self.box = SecretBox(key)

    def encrypt_text(self, text: str) -> tuple[bytes, bytes]:
        nonce = nacl_random(SecretBox.NONCE_SIZE)
        ct = self.box.encrypt(text.encode("utf-8"), nonce).ciphertext
        return ct, nonce

    def decrypt_text(self, ciphertext: bytes, nonce: bytes) -> str:
        pt = self.box.decrypt(ciphertext, nonce)
        return pt.decode("utf-8")

def _ip_prefix(self, ip: str) -> str:
    # Privacy-friendly ban key: IPv4 /24 or IPv6 /64 prefix.
    ip = (ip or "").strip()
    if ":" in ip:  # IPv6
        parts = ip.split(":")
        return ":".join(parts[:4])  # rough /64
    # IPv4
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3])  # /24
    return ip

def ip_lookup(self, ip: str) -> str:
    prefix = self._ip_prefix(ip).encode("utf-8")
    pepper = settings.ip_lookup_pepper.encode("utf-8")
    return hmac.new(pepper, prefix, hashlib.sha256).hexdigest()

    def email_lookup(self, email: str) -> str:
        norm = email.strip().lower().encode("utf-8")
        pepper = settings.email_lookup_pepper.encode("utf-8")
        return hmac.new(pepper, norm, hashlib.sha256).hexdigest()

crypto = ContentCrypto()

