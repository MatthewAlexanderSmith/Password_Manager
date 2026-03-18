# CogniVault — Backend

FastAPI backend for the CogniVault local-only password manager.

## Responsibilities

- FastAPI REST API (vault, entries, stub endpoints)
- SQLite schema and encrypted JSON storage
- Module integration (crypto, AI, frontend bridge)

## Setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## API Overview

| Method | Endpoint               | Description                                      | Status                 |
| :----- | :--------------------- | :----------------------------------------------- | :--------------------- |
| POST   | `/vault/unlock`        | Derive key from master password, store in memory | Implemented (stub KDF) |
| POST   | `/vault/lock`          | Wipe in-memory key                               | Pending                |
| GET    | `/vault/status`        | Return lock state                                | Pending                |
| GET    | `/entries`             | List all entries (metadata only)                 | Pending                |
| POST   | `/entries`             | Create entry with encrypted password             | Pending                |
| GET    | `/entries/{id}`        | Retrieve entry with decrypted password           | Pending                |
| PUT    | `/entries/{id}`        | Update entry                                     | Pending                |
| DELETE | `/entries/{id}`        | Delete entry                                     | Pending                |
| POST   | `/ai/score-password`   | Stub — to be implemented by Paul                 | Stub only              |
| POST   | `/breach/check`        | Stub — to be implemented by Paul                 | Stub only              |
| POST   | `/export/quantum-safe` | Stub — to be implemented by Omar                 | Stub only              |

## Security Notes

- Master password is never stored; only the derived key is held in memory
- All passwords are encrypted with AES-256-GCM before any disk write
- CORS is locked to localhost only
- KDF: Argon2id (memory=64MB, iterations=3) — stub currently active

## Branch

`feature/backend-api`
