# CogniVault — Local Password Manager

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688.svg)
![Security](https://img.shields.io/badge/Security-AES--GCM%20%2B%20Argon2id-green.svg)
![Platform](https://img.shields.io/badge/Platform-Local%20Desktop-orange.svg)
![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)

---

## Overview

CogniVault is a local-first password manager designed for secure offline storage of credentials. It avoids cloud dependency by keeping all sensitive data on the user’s machine, fully encrypted at rest.

The system is divided into modular components:

- Frontend (vanilla JavaScript, HTML, CSS)
- Backend API (FastAPI with SQLite)
- Cryptography layer (AES-256-GCM with Argon2id key derivation)
- Optional AI module for experimental password analysis

---

## Key Features

- Master password vault unlock system
- Secure key derivation using Argon2id
- AES-256-GCM encryption for stored passwords
- Local SQLite database storage
- Create, read, update, and delete credentials
- Search and filter functionality for entries
- Password strength estimation
- Breach checking support via API integration
- Import and export of vault data
- Encrypted backup and restore system
- Optional AI-based password analysis (experimental)
- Desktop-style interface using pywebview integration

---

## Architecture

The application follows a simple layered architecture:

Frontend (User Interface)
→ pywebview / HTTP bridge
→ FastAPI backend service
→ SQLite database
→ Cryptography layer (Argon2id + AES-GCM)

---

## Project Structure

feature/
├── frontend/          # User interface (HTML, CSS, JavaScript)
├── backend-api/       # FastAPI backend and route handlers
├── cryptography/      # Encryption, key derivation, and vault logic
└── ai-algorithm/      # Experimental AI-based password analysis

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/MatthewAlexanderSmith/Password_Manager.git
cd Password_Manager
```

---

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If no requirements file is available:

```bash
pip install fastapi uvicorn sqlite3 cryptography pydantic
```

---

### 4. Run the backend server

```bash
uvicorn backend-api.main:app --reload
```

---

### 5. Launch the frontend

If using pywebview:

```bash
python app.py
```

Alternatively, open:

```
frontend/index.html
```

---

## Usage

### Unlocking the vault

- Enter the master password
- The backend derives an encryption key using Argon2id
- The session is unlocked locally in memory

---

### Managing entries

- Add credentials including site, username, and password
- Passwords are encrypted before storage
- Data is stored securely in a local SQLite database

---

### Viewing and editing entries

- Entries are decrypted on demand
- Updates re-encrypt modified data before saving

---

## Security Model

- Argon2id used for key derivation from the master password
- AES-256-GCM used for authenticated encryption
- Unique nonce per encrypted entry
- Master key stored only in memory during session
- No cloud storage or external synchronisation
- Fully local execution environment

---

## AI Module (Experimental)

The AI component provides experimental features such as:

- Password strength classification
- Detection of weak password patterns
- Risk scoring heuristics

This module is optional and not required for core functionality.

---

## Backend API

| Method | Endpoint              | Description              |
|--------|----------------------|--------------------------|
| POST   | /vault/unlock        | Unlock the vault        |
| POST   | /vault/lock          | Lock the vault          |
| GET    | /vault/status        | Check vault status      |
| GET    | /entries             | List all entries        |
| POST   | /entries             | Create a new entry      |
| PUT    | /entries/{id}        | Update an entry         |
| DELETE | /entries/{id}        | Delete an entry         |

---

## Frontend Features

- Tab-based navigation
- Modal-based interaction system
- Password generator
- Password strength meter
- Clipboard integration
- Toast notifications
- Offline-first design

---

## Dependencies

- FastAPI
- Uvicorn
- SQLite
- Cryptography
- Pydantic
- pywebview

---

## License

This project is licensed under the MIT Licence.

