import pandas as pd
import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from features import extract_features


# ── Config ────────────────────────────────────────────────────────────────────
ROCKYOU_PATH = os.path.join("..", "data", "rockyou.txt")
MODEL_OUTPUT  = os.path.join("..", "models", "rf_model.pkl")
MAX_PASSWORDS = 200_000   # start with 200k, increase once it works


# ── Labelling heuristic ───────────────────────────────────────────────────────
def label_password(password: str) -> str:
    length = len(password)
    has_upper   = any(c.isupper() for c in password)
    has_lower   = any(c.islower() for c in password)
    has_digit   = any(c.isdigit() for c in password)
    has_symbol  = any(not c.isalnum() for c in password)
    variety     = sum([has_upper, has_lower, has_digit, has_symbol])

    if length >= 10 and variety >= 3:
        return "strong"
    elif length >= 7 and variety >= 2:
        return "medium"
    else:
        return "weak"


# ── Load dataset ──────────────────────────────────────────────────────────────
def load_rockyou(path: str, max_rows: int) -> list[str]:
    passwords = []
    with open(path, "r", encoding="latin-1") as f:
        for i, line in enumerate(f):
            if i >= max_rows:
                break
            pw = line.strip()
            if pw:
                passwords.append(pw)
    print(f"Loaded {len(passwords):,} passwords")
    return passwords


# ── Build feature matrix ──────────────────────────────────────────────────────
def build_dataset(passwords: list[str]) -> pd.DataFrame:
    rows = []
    for pw in passwords:
        features = extract_features(pw)
        features["label"] = label_password(pw)
        rows.append(features)
    return pd.DataFrame(rows)


# ── Train ─────────────────────────────────────────────────────────────────────
def train(df: pd.DataFrame):
    X = df.drop(columns=["label"])
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1        # use all CPU cores
    )

    print("Training...")
    model.fit(X_train, y_train)

    print("\n── Evaluation ──────────────────────────────")
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))

    return model


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    passwords = load_rockyou(ROCKYOU_PATH, MAX_PASSWORDS)
    df        = build_dataset(passwords)
    model     = train(df)

    joblib.dump(model, MODEL_OUTPUT)
    print(f"\nModel saved to {MODEL_OUTPUT}")