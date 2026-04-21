import base64
import os
from typing import Optional
from config import settings

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
except Exception:
    Fernet = None


def _derive_key_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))


def _get_fernet() -> Optional["Fernet"]:
    if Fernet is None:
        return None

    key = settings.token_encryption_key
    if not key:
        return None

    # If key is a valid Fernet key (44 chars), use directly
    try:
        if isinstance(key, str) and len(key) == 44:
            return Fernet(key.encode())
    except Exception:
        pass

    # Otherwise derive key from passphrase using app-specific salt
    salt_source = (settings.spotify_client_id or "figment_salt").encode()
    salt = salt_source[:16].ljust(16, b"0")
    try:
        fkey = _derive_key_from_passphrase(key, salt)
        return Fernet(fkey)
    except Exception:
        return None


def encrypt_value(plaintext: str) -> str:
    f = _get_fernet()
    if not f:
        # No encryption available; return plaintext (not recommended)
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    f = _get_fernet()
    if not f:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        # If decryption fails, return original value to avoid breaking
        return ciphertext


def is_enabled() -> bool:
    return _get_fernet() is not None
