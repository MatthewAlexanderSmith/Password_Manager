import joblib
import os
import pandas as pd
import warnings
from features import features_to_list

MODEL_PATH = os.path.join("..", "models", "rf_model.pkl")

# Load once at import time
model = joblib.load(MODEL_PATH)

LABEL_SCORES = {
    "weak":   0.2,
    "medium": 0.6,
    "strong": 1.0,
}

def score_password(password: str) -> float:
    """
    Returns a strength score between 0.0 and 1.0.
    0.2 = weak, 0.6 = medium, 1.0 = strong
    """
    features = features_to_list(password)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        label = model.predict([features])[0]
    return LABEL_SCORES[label]


if __name__ == "__main__":
    test_passwords = [
        "123456",
        "password",
        "Hello123",
        "Tr0ub4dor&3",
        "correct-horse-battery",
    ]
    for pw in test_passwords:
        print(f"{pw:<25} → {score_password(pw)}")