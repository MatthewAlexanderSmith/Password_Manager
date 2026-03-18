import hashlib

def derive_key(password: str, salt: bytes) -> bytes:
    return hashlib.sha256(password.encode() + salt).digest()