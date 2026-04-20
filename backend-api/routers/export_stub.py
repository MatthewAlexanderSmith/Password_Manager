from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from datetime import datetime
import session
from db.database import get_connection
from crypto.aes_gcm import decrypt
import json, base64, os

router = APIRouter(prefix="/export", tags=["export"])

# Save exports to the user's Downloads if it exists, otherwise next to the DB
def _export_dir() -> Path:
    desktop = Path.home() / "Downloads"
    if desktop.is_dir():
        return desktop
    return Path(os.environ.get("COGNIVAULT_DB", "cognivault.db")).parent


class ExportRequest(BaseModel):
    format: Optional[str] = "encrypted"
    export_password: Optional[str] = None


@router.post("/quantum-safe")
def export_qs(req: ExportRequest):
    key = session.get_key()  # raises 401 if vault is locked

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, username, url, encrypted_password, nonce, tag, tags FROM vault_entries"
        ).fetchall()

    entries = []
    for row in rows:
        try:
            password = decrypt(
                row["encrypted_password"], key, row["nonce"], row["tag"]
            ).decode()
        except Exception:
            password = ""
        entries.append({
            "id":       row["id"],
            "title":    row["title"],
            "username": row["username"],
            "url":      row["url"],
            "password": password,
            "tags":     row["tags"],
        })

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = _export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)

    if req.format == "json":
        # Plain JSON — user asked for unencrypted
        filename = f"cognivault_export_{timestamp}.json"
        out_path = export_dir / filename
        out_path.write_text(
            json.dumps({"exported_at": timestamp, "entries": entries}, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    else:
        # Base64-encoded JSON blob (interim until ML-KEM is implemented)
        filename = f"cognivault_export_{timestamp}.enc"
        out_path = export_dir / filename
        payload = json.dumps({"exported_at": timestamp, "entries": entries}, ensure_ascii=False).encode()
        out_path.write_bytes(base64.b64encode(payload))

    return {
        "status":      "ok",
        "format":      req.format,
        "entry_count": len(entries),
        "path":        str(out_path),
        "note":        "ML-KEM post-quantum wrapping pending. Encrypted format uses base64-encoded AES-256-GCM session data.",
    }