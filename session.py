from __future__ import annotations

from threading import RLock
from typing import Optional

from fastapi import HTTPException

_lock = RLock()
_key: Optional[bytes] = None


def set_key(key: bytes) -> None:
    global _key
    with _lock:
        _key = key


def get_key() -> bytes:
    with _lock:
        if _key is None:
            raise HTTPException(status_code=401, detail="Vault is locked")
        return _key


def clear_key() -> None:
    global _key
    with _lock:
        _key = None