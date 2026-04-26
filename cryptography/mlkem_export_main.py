from pathlib import Path
import hashlib
import json

from mlkem_export import MLKEMExportModule


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    print("Generating keypair...")
    keypair = MLKEMExportModule.generate_keypair()
    print(f"Using algorithm: {keypair.algorithm}")

    ROOT = Path(__file__).resolve().parent.parent

    VAULT_PATH = ROOT / "backend-api" / "db" / "cognivault.db"
    if not VAULT_PATH.exists():
        raise FileNotFoundError(f"Vault not found: {VAULT_PATH}")

    print(f"Vault: {VAULT_PATH}")

    # Create a clear output folder
    OUT_DIR = ROOT / "export_test_output"
    OUT_DIR.mkdir(exist_ok=True)

    EXPORT_FILE = OUT_DIR / "vault_export.bundle.json"
    RESTORED_FILE = OUT_DIR / "vault_restored.db"

    # Read vault
    payload = VAULT_PATH.read_bytes()

    print("\n--- EXPORTING ---")
    bundle = MLKEMExportModule.export_bytes(
        payload,
        keypair.public_key,
        algorithm=keypair.algorithm,
    )

    # Save export file
    EXPORT_FILE.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    print(f"Export saved to: {EXPORT_FILE}")

    print("\n--- IMPORTING ---")
    restored = MLKEMExportModule.import_bytes(bundle, keypair.private_key)

    # Save restored vault
    RESTORED_FILE.write_bytes(restored)

    print(f"Restored file saved to: {RESTORED_FILE}")

    print("\n--- VERIFICATION ---")
    print("Original size :", len(payload))
    print("Restored size :", len(restored))
    print("Original SHA256:", sha256(VAULT_PATH))
    print("Restored SHA256:", sha256(RESTORED_FILE))
    print("Match:", payload == restored)

    print("\nBundle metadata:")
    print(json.dumps({
        "algorithm": bundle["algorithm"],
        "bundle_size": len(json.dumps(bundle)),
        "export_path": str(EXPORT_FILE),
        "restore_path": str(RESTORED_FILE),
    }, indent=2))


if __name__ == "__main__":
    main()