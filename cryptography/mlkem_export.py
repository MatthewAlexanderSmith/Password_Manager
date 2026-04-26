from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import serialization

try:  # ML-KEM is only available on newer cryptography builds/backends.
    from cryptography.hazmat.primitives.asymmetric import mlkem 

    MLKEM_AVAILABLE = True
except Exception:
    mlkem = None  
    MLKEM_AVAILABLE = False



AAD = b"Password_Manager-MLKEM-Export-v1"
HKDF_INFO = b"Password_Manager export envelope v1"
DEFAULT_MLKEM_VARIANT = "mlkem768"
DEFAULT_FALLBACK_VARIANT = "x25519-hkdf"


@dataclass
class RecipientKeyPair:
    algorithm: str
    private_key: Any
    public_key: Any


class MLKEMExportModule:

    @staticmethod
    def generate_keypair(algorithm: Optional[str] = None) -> RecipientKeyPair:
        """Generate a recipient keypair."""

        chosen = (algorithm or (DEFAULT_MLKEM_VARIANT if MLKEM_AVAILABLE else DEFAULT_FALLBACK_VARIANT)).lower()

        if chosen in {"mlkem", "mlkem768", "kyber", "kyber768"}:
            if not MLKEM_AVAILABLE:
                raise RuntimeError(
                    "ML-KEM is not available in this Python environment; install a cryptography build with ML-KEM support."
                )
            try:
                private_key = mlkem.MLKEM768PrivateKey.generate()
                public_key = private_key.public_key()
                return RecipientKeyPair(DEFAULT_MLKEM_VARIANT, private_key, public_key)
            except UnsupportedAlgorithm as exc:
                raise RuntimeError("ML-KEM is not supported by the active backend.") from exc

        if chosen in {"x25519", "fallback", DEFAULT_FALLBACK_VARIANT}:
            private_key = x25519.X25519PrivateKey.generate()
            public_key = private_key.public_key()
            return RecipientKeyPair(DEFAULT_FALLBACK_VARIANT, private_key, public_key)

        raise ValueError(f"Unknown algorithm: {algorithm}")

    @staticmethod
    def _derive_aes_key(shared_secret: bytes, salt: bytes, context: bytes = b"") -> bytes:
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=HKDF_INFO + b"|" + context,
        )
        return hkdf.derive(shared_secret)

    @staticmethod
    def _b64(data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

    @staticmethod
    def _unb64(data: str) -> bytes:
        return base64.b64decode(data.encode("ascii"))

    @staticmethod
    def _serialize_public_key(algorithm: str, public_key: Any) -> str:
        if algorithm == DEFAULT_MLKEM_VARIANT:
            return MLKEMExportModule._b64(
                public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                )
            )
        if algorithm == DEFAULT_FALLBACK_VARIANT:
            return MLKEMExportModule._b64(public_key.public_bytes_raw())
        raise ValueError(f"Unsupported algorithm for serialization: {algorithm}")

    @staticmethod
    def _serialize_private_key(algorithm: str, private_key: Any) -> str:
        if algorithm == DEFAULT_MLKEM_VARIANT:
            return MLKEMExportModule._b64(private_key.private_bytes_raw())
        if algorithm == DEFAULT_FALLBACK_VARIANT:
            return MLKEMExportModule._b64(
                private_key.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        raise ValueError(f"Unsupported algorithm for serialization: {algorithm}")

    @staticmethod
    def _load_public_key(algorithm: str, public_key_b64: str):
        raw = MLKEMExportModule._unb64(public_key_b64)
        if algorithm == DEFAULT_MLKEM_VARIANT:
            if not MLKEM_AVAILABLE:
                raise RuntimeError("ML-KEM bundle was created, but ML-KEM support is not installed here.")
            return mlkem.MLKEM768PublicKey.from_public_bytes(raw)  # type: ignore[attr-defined]
        if algorithm == DEFAULT_FALLBACK_VARIANT:
            return x25519.X25519PublicKey.from_public_bytes(raw)
        raise ValueError(f"Unsupported algorithm for public key load: {algorithm}")

    @staticmethod
    def _load_private_key(algorithm: str, private_key_b64: str):
        raw = MLKEMExportModule._unb64(private_key_b64)
        if algorithm == DEFAULT_MLKEM_VARIANT:
            if not MLKEM_AVAILABLE:
                raise RuntimeError("ML-KEM bundle was created, but ML-KEM support is not installed here.")
            return mlkem.MLKEM768PrivateKey.from_seed_bytes(raw)  # type: ignore[attr-defined]
        if algorithm == DEFAULT_FALLBACK_VARIANT:
            return x25519.X25519PrivateKey.from_private_bytes(raw)
        raise ValueError(f"Unsupported algorithm for private key load: {algorithm}")

    @staticmethod
    def export_bytes(
        payload: bytes,
        recipient_public_key: Any,
        algorithm: str = DEFAULT_MLKEM_VARIANT,
        context: bytes = b"",
    ) -> dict[str, Any]:
        """Encrypt bytes into a JSON-serializable export bundle."""

        chosen = algorithm.lower()

        if chosen == DEFAULT_MLKEM_VARIANT:
            if not MLKEM_AVAILABLE:
                raise RuntimeError("ML-KEM is unavailable in this environment.")
            shared_secret, kem_ciphertext = recipient_public_key.encapsulate()  # type: ignore[attr-defined]
            kem_blob = MLKEMExportModule._b64(kem_ciphertext)
            kem_type = DEFAULT_MLKEM_VARIANT
        elif chosen == DEFAULT_FALLBACK_VARIANT:
            ephemeral_private = x25519.X25519PrivateKey.generate()
            ephemeral_public = ephemeral_private.public_key()
            shared_secret = ephemeral_private.exchange(recipient_public_key)
            kem_blob = MLKEMExportModule._b64(ephemeral_public.public_bytes_raw())
            kem_type = DEFAULT_FALLBACK_VARIANT
        else:
            raise ValueError(f"Unknown export algorithm: {algorithm}")

        salt = os.urandom(16)
        aes_key = MLKEMExportModule._derive_aes_key(shared_secret, salt, context=context)
        nonce = os.urandom(12)
        ciphertext = AESGCM(aes_key).encrypt(nonce, payload, AAD + b"|" + context)

        return {
            "version": 1,
            "algorithm": kem_type,
            "salt": MLKEMExportModule._b64(salt),
            "nonce": MLKEMExportModule._b64(nonce),
            "kem_ciphertext": kem_blob,
            "ciphertext": MLKEMExportModule._b64(ciphertext),
            "context": MLKEMExportModule._b64(context),
        }

    @staticmethod
    def import_bytes(bundle: dict[str, Any], recipient_private_key: Any) -> bytes:
        """Decrypt a previously exported bundle."""

        algorithm = bundle["algorithm"]
        salt = MLKEMExportModule._unb64(bundle["salt"])
        nonce = MLKEMExportModule._unb64(bundle["nonce"])
        kem_ciphertext = MLKEMExportModule._unb64(bundle["kem_ciphertext"])
        ciphertext = MLKEMExportModule._unb64(bundle["ciphertext"])
        context = MLKEMExportModule._unb64(bundle.get("context", ""))

        if algorithm == DEFAULT_MLKEM_VARIANT:
            shared_secret = recipient_private_key.decapsulate(kem_ciphertext)  # type: ignore[attr-defined]
        elif algorithm == DEFAULT_FALLBACK_VARIANT:
            ephemeral_public = x25519.X25519PublicKey.from_public_bytes(kem_ciphertext)
            shared_secret = recipient_private_key.exchange(ephemeral_public)
        else:
            raise ValueError(f"Unsupported bundle algorithm: {algorithm}")

        aes_key = MLKEMExportModule._derive_aes_key(shared_secret, salt, context=context)
        return AESGCM(aes_key).decrypt(nonce, ciphertext, AAD + b"|" + context)

    @staticmethod
    def export_file(
        input_path: str | Path,
        output_path: str | Path,
        recipient_public_key: Any,
        algorithm: str = DEFAULT_MLKEM_VARIANT,
        context: bytes = b"",
    ) -> Path:
        input_path = Path(input_path)
        output_path = Path(output_path)
        bundle = MLKEMExportModule.export_bytes(
            input_path.read_bytes(), recipient_public_key, algorithm=algorithm, context=context
        )
        output_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        return output_path

    @staticmethod
    def import_file(input_path: str | Path, recipient_private_key: Any, output_path: str | Path) -> Path:
        input_path = Path(input_path)
        output_path = Path(output_path)
        bundle = json.loads(input_path.read_text(encoding="utf-8"))
        output_path.write_bytes(MLKEMExportModule.import_bytes(bundle, recipient_private_key))
        return output_path

    @staticmethod
    def save_public_key(path: str | Path, keypair: RecipientKeyPair) -> Path:
        path = Path(path)
        path.write_text(
            json.dumps(
                {
                    "algorithm": keypair.algorithm,
                    "public_key": MLKEMExportModule._serialize_public_key(keypair.algorithm, keypair.public_key),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def save_private_key(path: str | Path, keypair: RecipientKeyPair) -> Path:
        path = Path(path)
        path.write_text(
            json.dumps(
                {
                    "algorithm": keypair.algorithm,
                    "private_key": MLKEMExportModule._serialize_private_key(keypair.algorithm, keypair.private_key),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def load_keypair(public_path: str | Path, private_path: str | Path) -> RecipientKeyPair:
        public_blob = json.loads(Path(public_path).read_text(encoding="utf-8"))
        private_blob = json.loads(Path(private_path).read_text(encoding="utf-8"))
        algorithm = public_blob["algorithm"]
        if algorithm != private_blob["algorithm"]:
            raise ValueError("Public/private key algorithm mismatch")
        public_key = MLKEMExportModule._load_public_key(algorithm, public_blob["public_key"])
        private_key = MLKEMExportModule._load_private_key(algorithm, private_blob["private_key"])
        return RecipientKeyPair(algorithm=algorithm, private_key=private_key, public_key=public_key)