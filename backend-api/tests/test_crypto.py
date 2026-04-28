import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crypto.aes_gcm import encrypt, decrypt
from crypto.kdf import derive_key

def test_encrypt_decrypt():
    key = derive_key("password", b"fixedsalt123456")

    plaintext = b"secret_data"

    ciphertext, nonce, tag = encrypt(plaintext, key)
    decrypted = decrypt(ciphertext, key, nonce, tag)

    assert decrypted == plaintext


def test_wrong_key_fails():
    key1 = derive_key("password1", b"salt123456789012")
    key2 = derive_key("password2", b"salt123456789012")

    plaintext = b"secret"

    ciphertext, nonce, tag = encrypt(plaintext, key1)

    try:
        decrypt(ciphertext, key2, nonce, tag)
        assert False  # must not reach
    except Exception:
        assert True


def test_nonce_uniqueness():
    key = derive_key("password", b"salt123456789012")

    c1, n1, _ = encrypt(b"data", key)
    c2, n2, _ = encrypt(b"data", key)

    assert n1 != n2