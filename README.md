# Password Manager

A local password manager built in Python with a focus on modern cryptography and straightforward local storage. This branch explores a hardened encryption approach for protecting individual vault entries, storing metadata separately, and supporting encrypted backups.

## Overview

This project is designed to keep passwords on the local machine rather than relying on a remote service. Each entry is encrypted with a master password, and the cryptographic workflow is handled by a dedicated service layer so that encryption, decryption, verification and file persistence remain separate concerns.

The current branch includes:

- `crypto_poc.py` for a simple end-to-end cryptographic proof of concept
- `crypto_service.py` for reusable encryption and file-handling logic
- `vault_manager.py` for vault storage, retrieval, deletion, backup and restore

## Features

- Argon2id key derivation from a master password and per-entry salt
- AES-256-GCM encryption for vault secrets
- Authentication data binding through additional authenticated data
- Secure handling of encrypted entry blobs stored as JSON
- SQLite-backed metadata store for vault entries
- Individual entry creation, listing, retrieval and deletion
- Encrypted backup creation
- Backup restoration from an encrypted archive
- Basic secure memory wiping for derived key material
- Local-first design with no required network connection

## Cryptography design

The cryptography branch uses the following approach:

### Key derivation

A master password is processed with Argon2id to derive a 256-bit encryption key. Each encryption operation uses its own random salt, so identical passwords do not produce identical encrypted output.

### Encryption

Vault data is encrypted with AES-GCM. This provides both confidentiality and integrity, which means tampering with the ciphertext should cause decryption to fail.

### Stored data

Encrypted payloads are written to JSON files containing:

- salt
- nonce
- ciphertext

The database stores metadata such as:

- entry ID
- site name
- username
- path to the encrypted JSON file
- creation timestamp

### Backups

Backups are produced as ZIP archives containing the SQLite database and encrypted entry files. If a master password is supplied, the backup archive itself can then be encrypted and saved as a `.enc` file.

## Project structure

```text
Password_Manager/
├── crypto_poc.py
├── crypto_service.py
└── vault_manager.py
```

## Requirements

- Python 3.10 or later
- `cryptography`
- `argon2-cffi`

Depending on how you run the project, you may also use the Python standard library modules already included with Python, such as `sqlite3`, `json`, `zipfile` and `logging`.

## Installation

Clone the repository and change into the project directory:

```bash
git clone https://github.com/MatthewAlexanderSmith/Password_Manager.git
cd Password_Manager
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS and Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install cryptography argon2-cffi
```

## Usage

The repository is currently organised around importable Python modules rather than a finished command-line interface. You can use the classes and functions directly from your own scripts.

### Using the cryptography service

```python
from crypto_service import CryptoService

master_password = "StrongMasterPassword!"
salt = b"0123456789abcdef"

key = CryptoService.derive_key(master_password, salt)
encrypted = CryptoService.encrypt_entry("my_secret_password", master_password)
decrypted = CryptoService.decrypt_entry(encrypted, master_password)

print(encrypted)
print(decrypted)
```

### Using the vault manager

```python
from vault_manager import VaultManager

manager = VaultManager()
master_password = "StrongMasterPassword!"

manager.add_entry(
    site_name="GitHub",
    username="murai_dev",
    password="git_secret_pass",
    master_password=master_password,
)

entries = manager.get_all_entries()
print(entries)

latest_entry_id = entries[-1][2]
password = manager.decrypt_vault_entry(latest_entry_id, master_password)
print(password)
```

### Creating a backup

```python
backup_path = manager.create_backup(master_password=master_password)
print(backup_path)
```

### Restoring from a backup

```python
restore_dir = manager.restore_from_backup(
    backup_path=backup_path,
    master_password=master_password,
)
print(restore_dir)
```

## Module notes

### `crypto_poc.py`

This file demonstrates the core cryptographic flow in a compact form. It shows how to derive a key, encrypt a secret, and decrypt it again.

### `crypto_service.py`

This module provides the reusable cryptographic interface used by the rest of the project.

Key responsibilities include:

- deriving keys with Argon2id
- encrypting and decrypting data with AES-GCM
- creating and checking a master password verification blob
- saving and loading encrypted JSON data

### `vault_manager.py`

This module manages the local vault storage layer.

Key responsibilities include:

- creating the SQLite table used for vault metadata
- adding new encrypted entries
- listing stored entries
- decrypting a selected entry
- securely deleting entry files
- creating backups and optional encrypted backups
- restoring a vault from an encrypted backup

## Security considerations

A few important points to keep in mind when working with this project:

- Use a strong master password.
- Keep backup files protected, especially encrypted backups, as they still rely on the master password for access.
- Treat local storage as sensitive data.
- Consider adding password strength checks, user authentication flow, and proper exception handling around any user interface in future work.
- Review file permissions and storage location before using the project on a shared machine.

## Current limitations

This branch is a focused technical foundation rather than a polished end-user application. It currently:

- does not expose a full graphical interface
- does not provide a finished command-line interface
- assumes the caller is comfortable working with Python modules
- uses sample values in the demonstration blocks, which should not be reused in real deployments

## Possible future improvements

- Add a proper command-line interface
- Build a desktop or web front end
- Introduce tests for encryption, decryption and backup flows
- Add password generation
- Support editing and rotating stored credentials
- Improve vault integrity checks and recovery workflows
- Add packaging and dependency pinning

## Licence

This project is licensed under the MIT Licence.

## Acknowledgements

This branch makes use of widely used Python cryptography libraries and the standard library SQLite module to keep the vault local, lightweight and easy to reason about.
