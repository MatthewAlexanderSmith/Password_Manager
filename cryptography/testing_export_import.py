from pathlib import Path
import hashlib
import sqlite3


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_sqlite_integrity(path: Path) -> bool:
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        result = cur.fetchone()[0]
        conn.close()
        return result == "ok"
    except Exception as e:
        print("SQLite error:", e)
        return False


def main():
    ROOT = Path(__file__).resolve().parent.parent

    original = ROOT / "backend-api" / "db" / "cognivault.db"
    restored = ROOT / "export_test_output" / "vault_restored.db"

    if not original.exists():
        raise FileNotFoundError(f"Missing original vault: {original}")

    if not restored.exists():
        raise FileNotFoundError(f"Missing restored vault: {restored}")

    print("\n--- VAULT VERIFICATION ---")

    # 1. Hash comparison
    orig_hash = sha256(original)
    rest_hash = sha256(restored)

    print("Original SHA256:", orig_hash)
    print("Restored SHA256:", rest_hash)
    print("Hash match:", orig_hash == rest_hash)

    # 2. SQLite integrity check
    print("\nChecking SQLite integrity...")

    orig_ok = check_sqlite_integrity(original)
    rest_ok = check_sqlite_integrity(restored)

    print("Original DB valid:", orig_ok)
    print("Restored DB valid:", rest_ok)

    # 3. Final verdict
    print("\n--- RESULT ---")

    if orig_hash == rest_hash and orig_ok and rest_ok:
        print("VAULT RESTORE IS PERFECT (identical + valid SQLite)")
    elif rest_ok:
        print("Vault restored but NOT identical (possible encryption round-trip difference)")
    else:
        print("Vault restore FAILED or corrupted")


if __name__ == "__main__":
    main()