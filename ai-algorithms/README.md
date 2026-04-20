# CogniVault — AI & Algorithms

Offline AI and breach-detection module for the CogniVault local-only password manager.

## Responsibilities

- Random Forest model for password strength scoring
- Bloom Filter breach checker against SHA-1 corpus
- Unit tests for both components

## Setup

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Structure

```
ai/
├── features.py        # Feature extraction from raw passwords
├── train.py           # Random Forest training script
├── scorer.py          # score_password() → 0.0 to 1.0
└── convert_to_sha1.py # Converts plaintext corpus to SHA-1

bloom/
└── breach_checker.py  # is_breached() via Bloom Filter

tests/
├── test_scorer.py     # 7 unit tests for scorer
└── test_breach.py     # 6 unit tests for breach checker

models/
└── rf_model.pkl       # Trained model (not committed to git)

data/
├── rockyou.txt        # Download from Kaggle
└── hibp_sample.txt    # Generated via convert_to_sha1.py
```

## API

| Function                    | Location                  | Description                            | Status         |
| --------------------------- | ------------------------- | -------------------------------------- | -------------- |
| `score_password(password)`  | `ai/scorer.py`            | Returns 0.2 / 0.6 / 1.0 strength score | ✅ Implemented |
| `is_breached(password, bf)` | `bloom/breach_checker.py` | Returns True/False from Bloom Filter   | ✅ Implemented |
| `build_bloom_filter(path)`  | `bloom/breach_checker.py` | Loads SHA-1 corpus into Bloom Filter   | ✅ Implemented |

## Datasets

- **rockyou.txt** — download from [Kaggle](https://www.kaggle.com/datasets/wjburns/common-password-list-rockyoutxt), place in `data/`
- **hibp_sample.txt** — generated locally by running `python ai/convert_to_sha1.py`

## Running Tests

```
pytest tests/ -v
# 13/13 tests passing
```

## Security Design

- Raw passwords are never stored — only SHA-1 hashes are loaded into the Bloom Filter
- Random Forest inference runs fully offline — no API calls, no data leakage
- Bloom Filter tuned to 1% false positive rate at 1M entries (~12MB memory)
