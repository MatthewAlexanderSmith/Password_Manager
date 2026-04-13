from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import session
from crypto.aes_gcm import encrypt
from db.database import get_connection

router = APIRouter(prefix="/import", tags=["import"])


class ImportRequest(BaseModel):
    content: str = Field(min_length=1)
    clear_existing: bool = False


def _parse_backup(content: str) -> dict[str, Any]:
    raw = content.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Import file is empty")

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {"entries": parsed}
    except json.JSONDecodeError:
        pass

    try:
        decoded = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Unsupported import file format")

    try:
        parsed = json.loads(decoded.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Decoded import payload is not valid JSON") from exc

    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        return {"entries": parsed}

    raise HTTPException(status_code=400, detail="Import payload is not a JSON object or list")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


@router.post("/quantum-safe")
def import_qs(req: ImportRequest):
    key = session.get_key()

    payload = _parse_backup(req.content)
    entries = payload.get("entries")

    if not isinstance(entries, list):
        raise HTTPException(status_code=400, detail="Import file does not contain an entries list")

    imported = 0
    skipped = []

    with get_connection() as conn:
        if req.clear_existing:
            conn.execute("DELETE FROM vault_entries")

        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                skipped.append({"index": idx, "reason": "Entry is not an object"})
                continue

            title = _clean_text(entry.get("title"))
            username = _clean_text(entry.get("username"))
            url = _clean_text(entry.get("url"))
            password = _clean_text(entry.get("password"))
            tags = _clean_text(entry.get("tags"))

            if not title:
                skipped.append({"index": idx, "reason": "Missing title"})
                continue
            if not password:
                skipped.append({"index": idx, "reason": "Missing password"})
                continue

            ciphertext, nonce, tag = encrypt(password.encode("utf-8"), key)

            conn.execute(
                """
                INSERT INTO vault_entries (title, username, url, encrypted_password, nonce, tag, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (title, username or None, url or None, ciphertext, nonce, tag, tags),
            )
            imported += 1

    return {
        "status": "ok",
        "imported": imported,
        "skipped": len(skipped),
        "errors": skipped,
    }
