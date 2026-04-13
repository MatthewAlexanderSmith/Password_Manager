# CogniVault Frontend

## Overview

CogniVault is a local-first, single-page password manager frontend built
with HTML, CSS, and vanilla JavaScript.\
This branch (`feature/frontend`) focuses entirely on the **client-side
interface**, handling UI, state, and communication with a backend API or
a `pywebview` bridge.

------------------------------------------------------------------------

## Frontend Architecture

The frontend is a **SPA (Single Page Application)** with: - No
frameworks (pure JS) - DOM-driven rendering - Tab-based navigation -
Centralized API handler logic

### Core Files

    index.html      → UI structure
    css/styles.css  → Styling
    js/app.js       → Application logic

------------------------------------------------------------------------

## Application Flow

### 1. Startup

-   App loads `index.html`
-   JS initializes event listeners
-   Checks `/vault/status`
-   Determines:
    -   Locked → show unlock screen
    -   Unlocked → load vault

------------------------------------------------------------------------

### 2. Unlock / Create Vault

-   User enters master password

-   Request sent to:

        POST /vault/unlock

-   If no vault exists → creation flow

-   On success:

    -   UI switches to dashboard
    -   Credentials are fetched

------------------------------------------------------------------------

### 3. Session State

Frontend maintains: - Locked / unlocked state - Cached credentials
list - Active tab - Temporary UI states (modals, toasts)

------------------------------------------------------------------------

## Credential Management (Frontend Behavior)

### Fetching Entries

    GET /entries

-   Populates credential list UI
-   Stored in memory for filtering/search

### Adding Entry

    POST /entries

Fields: - site - username - password

### Viewing Entry

    GET /entries/:id

-   Password hidden by default
-   Reveal toggle handled in UI

### Deleting Entry

    DELETE /entries/:id

-   Immediate UI update after success

### Search

-   Client-side filtering
-   Real-time input listener

------------------------------------------------------------------------

## Password Generator (Frontend Logic)

### Options

-   Length slider
-   Checkboxes:
    -   Uppercase
    -   Lowercase
    -   Numbers
    -   Symbols

### Generation Process

-   Build character pool
-   Random selection loop
-   Display result in UI
-   Copy button uses Clipboard API

------------------------------------------------------------------------

## Password Strength

### Local Evaluation

-   Basic heuristics:
    -   Length
    -   Character diversity

### Backend AI (Optional)

    POST /ai/score-password

-   Returns strength score
-   UI updates dynamically

------------------------------------------------------------------------

## Breach Detection

### Endpoint

    POST /breach/check

### Frontend Behavior

-   Sends password (or hash depending on backend)
-   Displays:
    -   Safe / Compromised
-   Uses toast + inline result display

------------------------------------------------------------------------

## Export / Import System

### Export

    POST /export/quantum-safe

Options: - Encrypted `.enc` - Plain JSON

Frontend: - Triggers file download - Handles blob response

### Import

    POST /import/quantum-safe

-   File input element
-   Sends file via FormData

------------------------------------------------------------------------

## Settings Page

Features: - Lock vault - Create backup - Security info display

### Backup

    POST /vault/backup

------------------------------------------------------------------------

## API Layer (Frontend Implementation)

### Priority Order

1.  `pywebview` bridge
2.  HTTP fallback:
    -   http://127.0.0.1:8000
    -   http://localhost:8000

### Wrapper Logic

-   Central request handler
-   Try/catch fallback
-   JSON parsing
-   Error handling via UI

------------------------------------------------------------------------

## UI Components

### Tabs

-   Vault
-   Generator
-   Breach
-   Settings

### Modals

-   Add entry
-   Import

### Toast Notifications

-   Success
-   Error
-   Info

### Forms

-   Controlled via JS
-   Prevent default submission

------------------------------------------------------------------------

## Styling (CSS)

-   Custom styles (no framework)
-   Responsive layout
-   Minimalist UI
-   Sections:
    -   Sidebar / navigation
    -   Content panels
    -   Forms
    -   Buttons

------------------------------------------------------------------------

## Security Considerations (Frontend)

-   No password persistence in localStorage
-   Sensitive data only in memory
-   Clipboard use is user-triggered
-   Password fields masked by default

------------------------------------------------------------------------

## Limitations

-   No frontend build system
-   No state management library
-   Depends heavily on backend for security
-   No offline persistence without backend

------------------------------------------------------------------------

## Running the Frontend

``` bash
git clone https://github.com/MatthewAlexanderSmith/Password_Manager.git
cd Password_Manager
git checkout feature/frontend
```

Run:

``` bash
python -m http.server 3000
```

Open:

    http://localhost:3000

------------------------------------------------------------------------

## License

MIT License
