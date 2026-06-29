from fastapi import Header, HTTPException
from typing import Optional
from services.supabase_client import supabase


async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        result = supabase.auth.get_user(token)
        return result.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
