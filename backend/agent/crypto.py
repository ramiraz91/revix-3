"""
Encryption utility for agent credentials.
Uses Fernet symmetric encryption derived from JWT_SECRET.
"""
import base64
import hashlib
from cryptography.fernet import Fernet
from config import JWT_SECRET


def _get_key() -> bytes:
    # Derive a Fernet-compatible key from JWT_SECRET
    digest = hashlib.sha256(JWT_SECRET.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(plaintext: str) -> str:
    f = Fernet(_get_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    f = Fernet(_get_key())
    return f.decrypt(ciphertext.encode()).decode()
