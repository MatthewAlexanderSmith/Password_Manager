import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import tempfile

_temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
_temp_db.close()
os.environ["COGNIVAULT_DB"] = _temp_db.name

from db.database import initialize_database  # noqa: E402
initialize_database()
from main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import pytest  # noqa: E402
import session  # noqa: E402

client = TestClient(app, raise_server_exceptions=True)

MASTER_PASSWORD = "test_master_123"


@pytest.fixture(autouse=True)
def reset_state():
    """Wipe session key and all data between tests for full isolation."""
    session.clear_key()
    from db.database import get_connection
    with get_connection() as conn:
        conn.execute("DELETE FROM vault_meta")
        conn.execute("DELETE FROM vault_entries")
    yield
    session.clear_key()


def unlock():
    # Create the vault (first run), ignore 409 if it already exists
    client.post("/vault/create", json={"password": MASTER_PASSWORD})
    return client.post("/vault/unlock", json={"password": MASTER_PASSWORD})

def test_unlock():
    res = unlock()
    assert res.status_code == 200
    assert "status" in res.json()


def test_create_and_get_entry():
    unlock()
    create_res = client.post(
        "/entries",
        json={
            "title": "Test",
            "username": "user",
            "password": "secret123",
        },
    )
    assert create_res.status_code == 200
    entry_id = create_res.json()["id"]

    get_res = client.get(f"/entries/{entry_id}")
    data = get_res.json()
    assert data["password"] == "secret123"
    assert data["title"] == "Test"


def test_list_entries_no_password():
    unlock()
    res = client.get("/entries")
    data = res.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "password" not in data[0]


def test_lock_blocks_access():
    unlock()
    client.post("/vault/lock")
    res = client.get("/entries")
    assert res.status_code == 401


def test_wrong_password_rejected():
    client.post("/vault/create", json={"password": MASTER_PASSWORD})
    client.post("/vault/lock")

    res = client.post(
        "/vault/unlock",
        json={"password": "wrong_password"},
    )
    assert res.status_code == 401