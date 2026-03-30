import os
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2.low_level import hash_secret_raw, Type

# CONFIG
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 64 * 1024
ARGON2_PARALLELISM = 2
KEY_LENGTH = 32
NONCE_SIZE = 12
SALT_SIZE = 16

AAD = b"cognivault-v1"


class CryptoService:

    # KEY DERIVATION
    @staticmethod
    def derive_key(master_password: str, salt: bytes) -> bytearray:
        key = hash_secret_raw(
            secret=master_password.encode(),
            salt=salt,
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=KEY_LENGTH,
            type=Type.ID,
        )
        return bytearray(key)  # mutable for wiping

    # SECURE MEMORY WIPE
    @staticmethod
    def secure_erase(data: bytearray):
        for i in range(len(data)):
            data[i] = 0

    # ENCRYPT ENTRY
    @staticmethod
    def encrypt_entry(password: str, master_password: str) -> dict:
        salt = os.urandom(SALT_SIZE)
        key = CryptoService.derive_key(master_password, salt)

        try:
            aesgcm = AESGCM(bytes(key))
            nonce = os.urandom(NONCE_SIZE)

            ciphertext = aesgcm.encrypt(nonce, password.encode(), AAD)

            return {
                "salt": salt.hex(),
                "nonce": nonce.hex(),
                "ciphertext": ciphertext.hex(),
            }

        finally:
            CryptoService.secure_erase(key)

    # DECRYPT ENTRY
    @staticmethod
    def decrypt_entry(data: dict, master_password: str) -> str:
        salt = bytes.fromhex(data["salt"])
        nonce = bytes.fromhex(data["nonce"])
        ciphertext = bytes.fromhex(data["ciphertext"])

        key = CryptoService.derive_key(master_password, salt)

        try:
            aesgcm = AESGCM(bytes(key))
            plaintext = aesgcm.decrypt(nonce, ciphertext, AAD)
            return plaintext.decode()

        except Exception:
            raise ValueError("Decryption failed — wrong password or tampered data")

        finally:
            CryptoService.secure_erase(key)

    # MASTER PASSWORD VERIFICATION
    @staticmethod
    def create_verification(master_password: str) -> dict:
        return CryptoService.encrypt_entry("vault_check", master_password)

    @staticmethod
    def verify_master_password(verification_data: dict, master_password: str) -> bool:
        try:
            result = CryptoService.decrypt_entry(verification_data, master_password)
            return result == "vault_check"
        except Exception:
            return False

    # FILE OPERATIONS
    @staticmethod
    def save_to_file(data: dict, filename: str):
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def load_from_file(filename: str) -> dict:
        with open(filename, "r") as f:
            return json.load(f)


# TEST
if __name__ == "__main__":
    master_password = "StrongMasterPassword!"
    vault_file = "vault_entry.json"
    verify_file = "verification.json"

    print("=== Creating verification ===")
    verification = CryptoService.create_verification(master_password)
    CryptoService.save_to_file(verification, verify_file)

    print("=== Verifying master password ===")
    loaded_ver = CryptoService.load_from_file(verify_file)
    print(
        "Correct password:",
        CryptoService.verify_master_password(loaded_ver, master_password),
    )
    print(
        "Wrong password:", CryptoService.verify_master_password(loaded_ver, "wrongpass")
    )

    print("\n=== Encrypting entry ===")
    encrypted_entry = CryptoService.encrypt_entry(
        "gmail_password_123!", master_password
    )
    CryptoService.save_to_file(encrypted_entry, vault_file)

    print("=== Decrypting entry ===")
    loaded = CryptoService.load_from_file(vault_file)
    decrypted = CryptoService.decrypt_entry(loaded, master_password)

    print("Recovered:", decrypted)
