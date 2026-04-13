import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_SIZE = 12  # required for GCM

def encrypt(plaintext: bytes, key: bytes) -> tuple[bytes, bytes, bytes]:
    nonce = os.urandom(NONCE_SIZE)

    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, None)

    # Split ciphertext + tag
    ciphertext = ciphertext_with_tag[:-16]
    tag = ciphertext_with_tag[-16:]

    return ciphertext, nonce, tag


def decrypt(ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes:
    aesgcm = AESGCM(key)

    combined = ciphertext + tag
    return aesgcm.decrypt(nonce, combined, None)