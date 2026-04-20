import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2.low_level import hash_secret_raw, Type

# CONFIG
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 64 * 1024  # 64 MB
ARGON2_PARALLELISM = 2
KEY_LENGTH = 32  # 256-bit
NONCE_SIZE = 12  # AES-GCM standard
SALT_SIZE = 16


# KEY DERIVATION (Argon2id)
def derive_key(master_password: str, salt: bytes) -> bytes:
    return hash_secret_raw(
        secret=master_password.encode(),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=KEY_LENGTH,
        type=Type.ID,
    )


# ENCRYPTION (AES-256-GCM)
def encrypt(plaintext: str, key: bytes) -> dict:
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_SIZE)

    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

    return {"nonce": nonce.hex(), "ciphertext": ciphertext.hex()}


# DECRYPTION
def decrypt(encrypted_data: dict, key: bytes) -> str:
    aesgcm = AESGCM(key)

    nonce = bytes.fromhex(encrypted_data["nonce"])
    ciphertext = bytes.fromhex(encrypted_data["ciphertext"])

    plaintext = aesgcm.decrypt(nonce, ciphertext, None)

    return plaintext.decode()


if __name__ == "__main__":
    master_password = "StrongMasterPassword!"
    salt = os.urandom(SALT_SIZE)

    key = derive_key(master_password, salt)

    secret = "my_super_secret_password"

    encrypted = encrypt(secret, key)
    print("Encrypted:", encrypted)

    decrypted = decrypt(encrypted, key)
    print("Decrypted:", decrypted)
