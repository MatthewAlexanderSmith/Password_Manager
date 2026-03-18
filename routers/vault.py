from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from crypto.kdf import derive_key
import os
import session

router = APIRouter(prefix="/vault", tags=["vault"])

class UnlockRequest(BaseModel):
    password: str

@router.post("/unlock")
def unlock(req: UnlockRequest):
    # TEMP salt (will move to DB later)
    salt = b"static_salt_123456"

    key = derive_key(req.password, salt)
    session.set_key(key)

    return {"status": "unlocked"}