import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai"))

from scorer import score_password


def test_weak_password():
    assert score_password("123456") == 0.2

def test_weak_password_common():
    assert score_password("password") == 0.2

def test_medium_password():
    assert score_password("Hello123") == 0.6

def test_strong_password():
    assert score_password("Tr0ub4dor&3") == 1.0

def test_empty_password():
    result = score_password("")
    assert result in [0.2, 0.6, 1.0]

def test_score_is_float():
    result = score_password("Hello123")
    assert isinstance(result, float)

def test_long_weak_password():
    # all lowercase, no variety → should still be weak
    assert score_password("aaaaaaaaaaaaaaaa") == 0.2