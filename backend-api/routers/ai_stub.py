from fastapi import APIRouter
from pydantic import BaseModel
import sys, os

router = APIRouter(prefix="/ai", tags=["ai"])

# Wire in the real Random Forest scorer from ai-algorithms/
_AI_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ai-algorithms", "ai")
if _AI_DIR not in sys.path:
    sys.path.insert(0, _AI_DIR)

try:
    from scorer import score_password as _rf_score
    _scorer_available = True
except Exception:
    _scorer_available = False


class PasswordInput(BaseModel):
    password: str


@router.post("/score-password")
def score_password(req: PasswordInput):
    if _scorer_available:
        try:
            score = int(_rf_score(req.password))
            label = "Weak" if score <= 20 else "Moderate" if score <= 60 else "Strong"
            return {"score": score, "label": label}
        except Exception:
            pass
    # Fallback: basic heuristic
    pw = req.password
    score = 0
    if len(pw) >= 8:  score += 10
    if len(pw) >= 12: score += 15
    if len(pw) >= 16: score += 15
    if any(c.isupper() for c in pw): score += 10
    if any(c.islower() for c in pw): score += 10
    if any(c.isdigit() for c in pw): score += 10
    if any(not c.isalnum() for c in pw): score += 15
    score = min(score, 100)
    label = "Weak" if score <= 20 else "Moderate" if score <= 60 else "Strong"
    return {"score": score, "label": label}
