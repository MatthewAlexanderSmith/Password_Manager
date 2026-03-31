from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import session
from crypto.kdf import derive_key
from crypto.aes_gcm import encrypt, decrypt
from db.database import get_connection

router = APIRouter(prefix="/vault", tags=["vault"])

SALT_KEY = "kdf_salt"
VERIFIER_KEY = "master_verifier"
VERIFIER_TEXT = b"cognivault-verifier"


class UnlockRequest(BaseModel):
    password: str


@router.post("/unlock")
def unlock(req: UnlockRequest):
    with get_connection() as conn:
        salt_row = conn.execute(
            "SELECT value FROM vault_meta WHERE key = ?",
            (SALT_KEY,),
        ).fetchone()

        if salt_row is None:
            salt = os.urandom(16)
            conn.execute(
                "INSERT INTO vault_meta(key, value) VALUES (?, ?)",
                (SALT_KEY, salt.hex()),
            )

            key = derive_key(req.password, salt)
            ciphertext, nonce, tag = encrypt(VERIFIER_TEXT, key)

            packed = f"{ciphertext.hex()}:{nonce.hex()}:{tag.hex()}"
            conn.execute(
                "INSERT INTO vault_meta(key, value) VALUES (?, ?)",
                (VERIFIER_KEY, packed),
            )
            conn.execute(
                "INSERT OR REPLACE INTO vault_meta(key, value) VALUES (?, ?)",
                ("last_unlock_at", datetime.now(timezone.utc).isoformat()),
            )

            session.set_key(key)
            return {"status": "unlocked", "first_run": True}

        salt = bytes.fromhex(salt_row["value"])
        key = derive_key(req.password, salt)

        verifier_row = conn.execute(
            "SELECT value FROM vault_meta WHERE key = ?",
            (VERIFIER_KEY,),
        ).fetchone()

        if verifier_row is None:
            raise HTTPException(status_code=500, detail="Vault verifier missing")

        try:
            ciphertext_hex, nonce_hex, tag_hex = verifier_row["value"].split(":")
            plaintext = decrypt(
                bytes.fromhex(ciphertext_hex),
                key,
                bytes.fromhex(nonce_hex),
                bytes.fromhex(tag_hex),
            )
            if plaintext != VERIFIER_TEXT:
                raise HTTPException(status_code=401, detail="Invalid master password")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid master password")

        conn.execute(
            "INSERT OR REPLACE INTO vault_meta(key, value) VALUES (?, ?)",
            ("last_unlock_at", datetime.now(timezone.utc).isoformat()),
        )

        session.set_key(key)
        return {"status": "unlocked", "first_run": False}
    
@router.post("/lock")
def lock():
    session.clear_key()
    return {"status": "locked"}


@router.get("/status")
def status():
    try:
        session.get_key()
        return {"locked": False}
    except HTTPException:
        return {"locked": True}