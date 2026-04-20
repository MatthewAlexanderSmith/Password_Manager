from __future__ import annotations

import io
import json
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from time import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import session
from crypto.aes_gcm import encrypt, decrypt
from crypto.kdf import derive_key
from db.database import get_connection

router = APIRouter(prefix="/vault", tags=["vault"])

SALT_KEY = "kdf_salt"
VERIFIER_KEY = "master_verifier"
VERIFIER_TEXT = b"cognivault-verifier"

FAILED_ATTEMPTS = {}
LOCKOUT_SECONDS = 10
MAX_ATTEMPTS = 5


class UnlockRequest(BaseModel):
    password: str


# ─── HELPERS ─────────────────────────────────────
def _backup_dir() -> Path:
    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        return downloads

    db_path = Path(
        os.environ.get(
            "COGNIVAULT_DB",
            str(Path(__file__).resolve().parents[1] / "db" / "cognivault.db"),
        )
    )
    return db_path.parent


def _vault_exists(conn) -> bool:
    row = conn.execute(
        "SELECT value FROM vault_meta WHERE key = ?",
        (SALT_KEY,),
    ).fetchone()
    return row is not None


# ─── CREATE VAULT (NEW) ───────────────────────────
@router.post("/create")
def create_vault(req: UnlockRequest):
    with get_connection() as conn:
        if _vault_exists(conn):
            raise HTTPException(status_code=409, detail="Vault already exists")

        salt = os.urandom(16)
        key = derive_key(req.password, salt)

        conn.execute(
            "INSERT INTO vault_meta(key, value) VALUES (?, ?)",
            (SALT_KEY, salt.hex()),
        )

        ciphertext, nonce, tag = encrypt(VERIFIER_TEXT, key)
        packed = f"{ciphertext.hex()}:{nonce.hex()}:{tag.hex()}"

        conn.execute(
            "INSERT INTO vault_meta(key, value) VALUES (?, ?)",
            (VERIFIER_KEY, packed),
        )

        conn.execute(
            "INSERT OR REPLACE INTO vault_meta(key, value) VALUES (?, ?)",
            ("created_at", datetime.now(timezone.utc).isoformat()),
        )

        session.set_key(key)

        return {"status": "created"}


# ─── UNLOCK (FIXED) ──────────────────────────────
@router.post("/unlock")
def unlock(req: UnlockRequest):
    client_id = "local"
    now = time()

    if client_id in FAILED_ATTEMPTS:
        attempts, last_time = FAILED_ATTEMPTS[client_id]
        if attempts >= MAX_ATTEMPTS and now - last_time < LOCKOUT_SECONDS:
            raise HTTPException(status_code=429, detail="Too many attempts. Try later")

    with get_connection() as conn:
        if not _vault_exists(conn):
            raise HTTPException(
                status_code=409,
                detail="Vault not initialized. Create a vault first."
            )

        salt_row = conn.execute(
            "SELECT value FROM vault_meta WHERE key = ?",
            (SALT_KEY,),
        ).fetchone()

        verifier_row = conn.execute(
            "SELECT value FROM vault_meta WHERE key = ?",
            (VERIFIER_KEY,),
        ).fetchone()

        if verifier_row is None:
            raise HTTPException(status_code=500, detail="Vault verifier missing")

        salt = bytes.fromhex(salt_row["value"])
        key = derive_key(req.password, salt)

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
            attempts, _ = FAILED_ATTEMPTS.get(client_id, (0, now))
            FAILED_ATTEMPTS[client_id] = (attempts + 1, now)
            raise HTTPException(status_code=401, detail="Invalid master password")

        conn.execute(
            "INSERT OR REPLACE INTO vault_meta(key, value) VALUES (?, ?)",
            ("last_unlock_at", datetime.now(timezone.utc).isoformat()),
        )

        session.set_key(key)
        return {"status": "unlocked"}


# ─── LOCK ────────────────────────────────────────
@router.post("/lock")
def lock():
    session.clear_key()
    return {"status": "locked"}


# ─── STATUS (UPDATED) ────────────────────────────
@router.get("/status")
def status():
    with get_connection() as conn:
        exists = _vault_exists(conn)

    try:
        session.get_key()
        return {"exists": exists, "locked": False}
    except HTTPException:
        return {"exists": exists, "locked": True}


# ─── BACKUP ──────────────────────────────────────
@router.post("/backup")
def backup():
    key = session.get_key()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    export_dir = _backup_dir()
    export_dir.mkdir(parents=True, exist_ok=True)

    out_path = export_dir / f"cognivault_backup_{timestamp}.zip.enc"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        snapshot_path = tmpdir_path / "cognivault.db"

        with get_connection() as src_conn:
            entry_count = src_conn.execute(
                "SELECT COUNT(*) AS c FROM vault_entries"
            ).fetchone()["c"]

            metadata_count = src_conn.execute(
                "SELECT COUNT(*) AS c FROM vault_meta"
            ).fetchone()["c"]

            dest_conn = sqlite3.connect(snapshot_path)
            try:
                src_conn.backup(dest_conn)
            finally:
                dest_conn.close()

        manifest = {
            "app": "CogniVault",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "entry_count": entry_count,
            "metadata_count": metadata_count,
            "format": "sqlite-backup",
        }

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(snapshot_path, arcname="cognivault.db")
            zf.writestr(
                "manifest.json",
                json.dumps(manifest, indent=2, ensure_ascii=False),
            )

        ciphertext, nonce, tag = encrypt(zip_buffer.getvalue(), key)

        out_path.write_bytes(b"CGBK1" + nonce + tag + ciphertext)

    return {
        "status": "ok",
        "path": str(out_path),
        "entry_count": entry_count,
        "metadata_count": metadata_count,
    }