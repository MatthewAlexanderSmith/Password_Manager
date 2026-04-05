# CogniVault – AI & Algorithms Module

**Developer:** Paul  
**Branch:** `feature/ai-algorithms`  
**Module:** MI204 – Proiect software în echipă

---

## Overview

This module provides two core components for CogniVault:

1. **Password Strength Scorer** – offline Random Forest model
2. **Breach Checker** – Bloom Filter against SHA-1 breach corpus

---

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

---

## Setup

```bash
pip install scikit-learn pandas numpy joblib pytest bloom-filter2
```

---

## Usage

```python
from ai.scorer import score_password
from bloom.breach_checker import build_bloom_filter, is_breached

# Score a password (0.2=weak, 0.6=medium, 1.0=strong)
score = score_password("Tr0ub4dor&3")  # → 1.0

# Check against breach corpus
bf = build_bloom_filter("data/hibp_sample.txt")
breached = is_breached("123456", bf)   # → True
```

---

## Tests

```bash
pytest tests/ -v
# 13/13 tests passing
```
