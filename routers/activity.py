from fastapi import APIRouter, Depends
from auth import get_current_user
from services.supabase_client import supabase

router = APIRouter()


@router.get("")
async def get_activity(limit: int = 20, user=Depends(get_current_user)):
    result = (
        supabase.table("activity_logs")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []
