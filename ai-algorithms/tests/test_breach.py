import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bloom"))

from breach_checker import build_bloom_filter, is_breached, sha1_hash

HIBP_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "hibp_sample.txt")

# Build filter once for all tests
bf = build_bloom_filter(HIBP_PATH, max_entries=1_000_000)


def test_known_breached_password():
    assert is_breached("123456", bf) == True

def test_known_breached_password_2():
    assert is_breached("password", bf) == True

def test_strong_not_breached():
    assert is_breached("xK9#mP2$qL8!nR5@", bf) == False

def test_sha1_hash_format():
    result = sha1_hash("password")
    assert len(result) == 40
    assert result == result.upper()

def test_is_breached_returns_bool():
    result = is_breached("123456", bf)
    assert isinstance(result, bool)

def test_random_strong_not_breached():
    assert is_breached("Zx#9!mK2@pL5$qR8", bf) == False