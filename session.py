from typing import Optional

_key: Optional[bytes] = None

def set_key(key: bytes):
    global _key
    _key = key

def get_key() -> bytes:
    if _key is None:
        raise ValueError("Vault is locked")
    return _key

def clear_key():
    global _key
    _key = None