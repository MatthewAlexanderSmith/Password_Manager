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

| Method | Endpoint             | Description                                      | Status         |
| ------ | -------------------- | ------------------------------------------------ | -------------- |
| POST   | /vault/unlock        | Derive key from master password, store in memory | ✅ Implemented |
| POST   | /vault/lock          | Wipe in-memory key                               | ✅ Implemented |
| GET    | /vault/status        | Return lock state                                | ✅ Implemented |
| GET    | /entries             | List all entries (metadata only)                 | ✅ Implemented |
| POST   | /entries             | Create entry with encrypted password             | ✅ Implemented |
| GET    | /entries/{id}        | Retrieve entry with decrypted password           | ✅ Implemented |
| PUT    | /entries/{id}        | Update entry                                     | ✅ Implemented |
| DELETE | /entries/{id}        | Delete entry                                     | ✅ Implemented |
| POST   | /ai/score-password   | Stub — to be implemented by Paul                 | 🔲 Stub only   |
| POST   | /breach/check        | Stub — to be implemented by Paul                 | 🔲 Stub only   |
| POST   | /export/quantum-safe | Stub — to be implemented by Omar                 | 🔲 Stub only   |

## Architecture

```
cognivault-backend/
├── main.py                  # FastAPI app, CORS, DB init on startup
├── session.py               # Thread-safe in-memory key store
├── requirements.txt
├── db/
│   ├── database.py          # SQLite connection, WAL mode, context manager
│   └── schema.sql           # vault_entries + vault_meta tables
├── crypto/
│   ├── aes_gcm.py           # AES-256-GCM encrypt/decrypt
│   └── kdf.py               # Argon2id key derivation (64MB, 3 iter)
├── routers/
│   ├── vault.py             # /vault/unlock, /lock, /status
│   ├── entries.py           # /entries CRUD (partial)
│   ├── ai_stub.py           # /ai/score-password stub
│   ├── breach_stub.py       # /breach/check stub
│   └── export_stub.py       # /export/quantum-safe stub
└── tests/
    ├── test_crypto.py
    └── test_entries.py
```

## Security Design

- **Master password** is never stored — only the Argon2id-derived key is held in memory
- **Salt** is generated on first unlock, persisted in `vault_meta` as hex
- **Verifier blob** (AES-GCM encrypted) stored in `vault_meta` to validate master password on subsequent unlocks without storing the password itself
- **All passwords** are encrypted with AES-256-GCM before any disk write; ciphertext, nonce, and tag stored as separate BLOBs in SQLite
- **CORS** locked to localhost only
- **Session** is thread-safe (RLock); all protected routes return HTTP 401 when vault is locked
- **KDF:** Argon2id — memory=64MB, iterations=3, parallelism=4, output=32 bytes
- **Brute-force protection:** in-memory lockout after 5 failed unlock attempts (10 second cooldown); returns HTTP 429
- **Input validation:** all entry fields have enforced length limits (title 1–100 chars, password 1–512 chars, etc.) — empty or oversized input returns HTTP 422

## Quick Test (Manual)

```bash
# 1. Start server
uvicorn main:app --reload

# 2. First unlock (initialises vault + salt)
curl -X POST http://127.0.0.1:8000/vault/unlock -H "Content-Type: application/json" -d "{\"password\": \"master123\"}"
# → {"status":"unlocked","first_run":true}

# 3. Create an entry
curl -X POST http://127.0.0.1:8000/entries -H "Content-Type: application/json" -d "{\"title\":\"Gmail\",\"username\":\"me\",\"password\":\"secret123\"}"
# → {"id":1}

# 4. Retrieve and decrypt
curl http://127.0.0.1:8000/entries/1
# → {"id":1,"title":"Gmail","username":"me","url":null,"password":"secret123","tags":""}

# 5. Lock vault
curl -X POST http://127.0.0.1:8000/vault/lock

# 6. Confirm access is blocked
curl http://127.0.0.1:8000/entries/1
# → {"detail":"Vault is locked"}
```

## Running Tests

```bash
python -m pytest
```

8 tests total across two files:

- `tests/test_crypto.py` — AES-GCM encrypt/decrypt roundtrip, wrong-key rejection, nonce uniqueness
- `tests/test_entries.py` — unlock flow, encrypted entry create/retrieve, list without password field, lock enforcement, wrong password rejection

Tests use an isolated temporary SQLite database and never touch the real vault file.
