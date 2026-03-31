from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from crypto.aes_gcm import encrypt, decrypt
from db.database import get_connection
import session

router = APIRouter(prefix="/entries", tags=["entries"])


class EntryCreate(BaseModel):
    title: str
    username: str | None = None
    url: str | None = None
    password: str
    tags: str | None = ""


@router.post("")
def create_entry(req: EntryCreate):
    key = session.get_key()

    ciphertext, nonce, tag = encrypt(req.password.encode(), key)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO vault_entries
            (title, username, url, encrypted_password, nonce, tag, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req.title,
                req.username,
                req.url,
                ciphertext,
                nonce,
                tag,
                req.tags,
            ),
        )

        entry_id = cursor.lastrowid

    return {"id": entry_id}

@router.get("/{entry_id}")
def get_entry(entry_id: int):
    key = session.get_key()

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM vault_entries WHERE id = ?",
            (entry_id,),
        ).fetchone()

        if row is None:
            return {"error": "Not found"}

        password = decrypt(
            row["encrypted_password"],
            key,
            row["nonce"],
            row["tag"],
        ).decode()

    return {
        "id": row["id"],
        "title": row["title"],
        "username": row["username"],
        "url": row["url"],
        "password": password,
        "tags": row["tags"],
    }