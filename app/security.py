import base64, os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import settings


def _key() -> bytes:
    if not settings.secret_key: raise RuntimeError("未配置 WALISSH_SECRET_KEY")
    return settings.secret_key.encode("utf-8")[:32].ljust(32, b"\0")


def encrypt(value: str | None) -> str | None:
    if not value: return value
    iv=os.urandom(12); return base64.b64encode(iv+AESGCM(_key()).encrypt(iv,value.encode(),None)).decode()


def decrypt(value: str | None, encrypted: int) -> str | None:
    if not value or not encrypted: return value
    raw=base64.b64decode(value); return AESGCM(_key()).decrypt(raw[:12],raw[12:],None).decode()
