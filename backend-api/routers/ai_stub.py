from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/ai", tags=["ai"])

# ============================
# AI MODULE INTEGRATION POINT
# ============================
# Owner: Paul / Omar
#
# Contract:
# - Input: { "password": str }
# - Output: { "score": int }  (0–100 recommended scale)
#
# Constraints:
# - MUST remain local-only (no external API calls)
# - MUST be fast (<100ms target)
# - No logging of plaintext passwords
#
# Replace the implementation of `score_password` only.
# Do NOT change route path or request/response schema.


class PasswordInput(BaseModel):
    password: str


@router.post("/score-password")
def score_password(req: PasswordInput):
    return {"score": 0}  # placeholder