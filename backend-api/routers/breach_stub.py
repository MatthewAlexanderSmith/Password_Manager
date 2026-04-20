from fastapi import APIRouter
from pydantic import BaseModel
import sys, os, hashlib, urllib.request

router = APIRouter(prefix="/breach", tags=["breach"])

# ── Local Bloom filter (optional, requires ai-algorithms/data/hibp_sample.txt) ──
_BLOOM_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ai-algorithms", "bloom")
_DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "..", "ai-algorithms", "data")
_HIBP_PATH = os.path.join(_DATA_DIR, "hibp_sample.txt")

if _BLOOM_DIR not in sys.path:
    sys.path.insert(0, _BLOOM_DIR)

_bloom_filter = None

def _try_load_bloom():
    global _bloom_filter
    if _bloom_filter is not None:
        return _bloom_filter
    if not os.path.isfile(_HIBP_PATH):
        return None
    try:
        from breach_checker import build_bloom_filter
        _bloom_filter = build_bloom_filter(_HIBP_PATH)
    except Exception:
        pass
    return _bloom_filter

_try_load_bloom()


def _sha1(password: str) -> str:
    return hashlib.sha1(password.encode("utf-8")).hexdigest().upper()


def _check_hibp_api(password: str) -> bool:
    """
    HIBP k-anonymity: sends only the first 5 chars of the SHA-1 hash.
    The full hash (and plaintext) never leave this machine.
    """
    sha1 = _sha1(password)
    prefix, suffix = sha1[:5], sha1[5:]
    url = f"https://api.pwnedpasswords.com/range/{prefix}"
    try:
        req = urllib.request.Request(url, headers={"Add-Padding": "true", "User-Agent": "CogniVault/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
        for line in body.splitlines():
            parts = line.split(":")
            if len(parts) == 2 and parts[0].upper() == suffix:
                return True
        return False
    except Exception:
        return None  # None = unknown (network unavailable)


# Well-known breached passwords — always checked locally regardless of network
_KNOWN_BREACHED_SHA1 = {
    _sha1(p) for p in [
        "123456", "password", "123456789", "12345678", "12345",
        "qwerty", "abc123", "111111", "1234567", "password1",
        "admin", "letmein", "welcome", "monkey", "dragon",
        "iloveyou", "sunshine", "princess", "master", "login",
        "pass", "test", "qwerty123", "000000", "1q2w3e",
    ]
}


class PasswordInput(BaseModel):
    password: str


@router.post("/check")
def check_breach(req: PasswordInput):
    sha1 = _sha1(req.password)

    # 1. Always check local known-breached list first (instant, offline)
    if sha1 in _KNOWN_BREACHED_SHA1:
        return {"breached": True, "source": "local"}

    # 2. Use Bloom filter if the local dataset was built
    bf = _bloom_filter or _try_load_bloom()
    if bf is not None:
        try:
            from breach_checker import is_breached
            return {"breached": is_breached(req.password, bf), "source": "bloom"}
        except Exception:
            pass

    # 3. Fall back to HIBP k-anonymity API (privacy-safe: only 5-char hash prefix sent)
    result = _check_hibp_api(req.password)
    if result is not None:
        return {"breached": result, "source": "hibp"}

    # 4. Network unavailable and no local data — return unknown
    return {"breached": False, "source": "unavailable"}