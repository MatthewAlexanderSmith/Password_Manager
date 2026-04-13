# CogniVault Frontend

CogniVault is a local-first password manager frontend designed for
secure vault access, credential management, password generation, breach
checking, and encrypted backups.

This branch (`feature/frontend`) contains the complete frontend
implementation built as a lightweight single-page application using
HTML, CSS, and vanilla JavaScript.

------------------------------------------------------------------------

## Features

### Vault Management

-   Unlock an existing vault using a master password
-   Create a new vault on first use
-   Lock the vault at any time

### Credential Management

-   Add, view, search, and delete credentials
-   Reveal and copy passwords securely
-   Clean and simple credential listing interface

### Password Generator

-   Generate strong passwords with:
    -   Adjustable length
    -   Uppercase letters
    -   Lowercase letters
    -   Numbers
    -   Symbols
-   One-click copy to clipboard

### Password Strength Analysis

-   Local password strength estimation
-   Optional backend AI scoring (if available)

### Breach Detection

-   Check passwords against a large breach dataset
-   Uses Bloom filter-based lookup
-   Fast and privacy-preserving

### Backup & Export

-   Export encrypted vault (`.enc`)
-   Export plaintext JSON (for backup purposes only)
-   Import backups
-   Create encrypted backups from settings

------------------------------------------------------------------------

## Security Overview

-   Master password is **never stored**
-   Key derivation via **Argon2id**
-   Encryption via **AES-256-GCM**
-   Quantum-safe export using **ML-KEM (Kyber768)**

------------------------------------------------------------------------

## Tech Stack

-   HTML5
-   CSS3
-   Vanilla JavaScript

------------------------------------------------------------------------

## Getting Started

``` bash
git clone https://github.com/MatthewAlexanderSmith/Password_Manager.git
cd Password_Manager
git checkout feature/frontend
```

Run locally:

``` bash
python -m http.server 3000
```

------------------------------------------------------------------------

## Project Structure

    Password_Manager/
    ├── index.html
    ├── css/
    │   └── styles.css
    └── js/
        └── app.js

------------------------------------------------------------------------

## License

MIT License
