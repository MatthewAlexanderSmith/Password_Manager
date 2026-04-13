import hashlib
import os
from bloom_filter2 import BloomFilter

HIBP_PATH   = os.path.join("..", "data", "hibp_sample.txt")
BLOOM_PATH  = os.path.join("..", "models", "bloom.pkl")

# ── Build ─────────────────────────────────────────────────────────────────────
def build_bloom_filter(hibp_path: str, max_entries: int = 1_000_000, error_rate: float = 0.01):
    """
    Reads the HIBP SHA-1 dataset and loads hashes into a Bloom Filter.
    max_entries: how many hashes to load (start small, scale up)
    error_rate:  false positive rate (0.01 = 1%)
    """
    print(f"Building Bloom Filter — {max_entries:,} entries at {error_rate*100}% FPR...")
    bf = BloomFilter(max_elements=max_entries, error_rate=error_rate)

    loaded = 0
    with open(hibp_path, "r", encoding="utf-8") as f:
        for line in f:
            if loaded >= max_entries:
                break
            parts = line.strip().split(":")
            if len(parts) == 2:
                sha1_hash = parts[0].upper()
                bf.add(sha1_hash)
                loaded += 1

    print(f"Loaded {loaded:,} hashes into Bloom Filter")
    return bf


# ── Check ─────────────────────────────────────────────────────────────────────
def sha1_hash(password: str) -> str:
    """Returns the uppercase SHA-1 hash of a password."""
    return hashlib.sha1(password.encode("utf-8")).hexdigest().upper()


def is_breached(password: str, bf: BloomFilter) -> bool:
    """
    Returns True if the password appears in the breach corpus.
    Uses SHA-1 hashing — raw password never stored or transmitted.
    """
    return sha1_hash(password) in bf


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Build the filter from HIBP dataset
    bf = build_bloom_filter(HIBP_PATH, max_entries=1_000_000)

    # Test with known breached passwords
    test_passwords = [
        "123456",
        "password",
        "Hello123",
        "Tr0ub4dor&3",
        "xK9#mP2$qL8!nR5@",   # random — should NOT be breached
    ]

    print("\n── Breach Check Results ─────────────────────")
    for pw in test_passwords:
        result = is_breached(pw, bf)
        status = "⚠ BREACHED" if result else "✓ Not found"
        print(f"{pw:<30} → {status}")