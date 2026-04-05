from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from crypto.aes_gcm import encrypt, decrypt
from db.database import get_connection
import session

router = APIRouter(prefix="/entries", tags=["entries"])


class EntryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    username: str | None = Field(default=None, max_length=100)
    url: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=1, max_length=512)
    tags: str | None = Field(default="", max_length=255)

class EntryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    username: str | None = Field(default=None, max_length=100)
    url: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=1, max_length=512)
    tags: str | None = Field(default=None, max_length=255)


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
            raise HTTPException(status_code=404, detail="Entry not found")

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

@router.get("")
def list_entries():
    session.get_key()  # enforce unlocked

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, username, url, tags, created_at, updated_at
            FROM vault_entries
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "username": row["username"],
            "url": row["url"],
            "tags": row["tags"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]

@router.delete("/{entry_id}")
def delete_entry(entry_id: int):
    session.get_key()

    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM vault_entries WHERE id = ?",
            (entry_id,),
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entry not found")

    return {"status": "deleted"}

@router.put("/{entry_id}")
def update_entry(entry_id: int, req: EntryUpdate):
    key = session.get_key()

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM vault_entries WHERE id = ?",
            (entry_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Entry not found")

        # Prepare updated values
        title = req.title if req.title is not None else row["title"]
        username = req.username if req.username is not None else row["username"]
        url = req.url if req.url is not None else row["url"]
        tags = req.tags if req.tags is not None else row["tags"]

        ciphertext = row["encrypted_password"]
        nonce = row["nonce"]
        tag = row["tag"]

        # If password updated → re-encrypt
        if req.password is not None:
            ciphertext, nonce, tag = encrypt(req.password.encode(), key)

        conn.execute(
            """
            UPDATE vault_entries
            SET title = ?, username = ?, url = ?, tags = ?,
                encrypted_password = ?, nonce = ?, tag = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                title,
                username,
                url,
                tags,
                ciphertext,
                nonce,
                tag,
                entry_id,
            ),
        )

    return {"status": "updated"}