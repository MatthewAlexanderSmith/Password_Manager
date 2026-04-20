import re
import math
from collections import Counter


def calculate_entropy(password: str) -> float:
    """Shannon entropy of the password."""
    if not password:
        return 0.0
    counts = Counter(password)
    length = len(password)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def has_common_substitutions(password: str) -> bool:
    """Checks for leet-speak style substitutions like @ for a, 0 for o."""
    patterns = re.compile(r'[@!3105$]')
    return bool(patterns.search(password))


def extract_features(password: str) -> dict:
    """
    Extracts a feature dictionary from a raw password string.
    This is what gets fed into the Random Forest model.
    """
    return {
        "length":               len(password),
        "num_uppercase":        sum(1 for c in password if c.isupper()),
        "num_lowercase":        sum(1 for c in password if c.islower()),
        "num_digits":           sum(1 for c in password if c.isdigit()),
        "num_symbols":          sum(1 for c in password if not c.isalnum()),
        "entropy":              calculate_entropy(password),
        "has_substitutions":    int(has_common_substitutions(password)),
        "max_consecutive":      max_consecutive_chars(password),
        "unique_chars":         len(set(password)),
    }


def max_consecutive_chars(password: str) -> int:
    """Returns the longest run of the same character, e.g. 'aaa' → 3."""
    if not password:
        return 0
    max_run = 1
    current_run = 1
    for i in range(1, len(password)):
        if password[i] == password[i - 1]:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1
    return max_run


def features_to_list(password: str) -> list:
    """Returns features as an ordered list for the model input."""
    f = extract_features(password)
    return [
        f["length"],
        f["num_uppercase"],
        f["num_lowercase"],
        f["num_digits"],
        f["num_symbols"],
        f["entropy"],
        f["has_substitutions"],
        f["max_consecutive"],
        f["unique_chars"],
    ]