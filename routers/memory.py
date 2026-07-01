from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import get_current_user
from services import memory as mem

router = APIRouter()


# ── TASK HISTORY ─────────────────────────────────────────────────────────────

@router.get("/{agent_id}/history")
async def task_history(agent_id: str, user=Depends(get_current_user)):
    return mem.get_task_history(agent_id, user.id)


# ── WORKER NOTES ─────────────────────────────────────────────────────────────

@router.get("/{agent_id}/notes")
async def get_notes(agent_id: str, user=Depends(get_current_user)):
    return {"notes": mem.get_worker_notes(agent_id, user.id)}


class NotesPayload(BaseModel):
    content: str

@router.put("/{agent_id}/notes")
async def update_notes(agent_id: str, payload: NotesPayload, user=Depends(get_current_user)):
    mem.set_worker_notes(agent_id, user.id, payload.content)
    return {"success": True}


# ── USER PREFERENCES ─────────────────────────────────────────────────────────

@router.get("/preferences")
async def get_preferences(user=Depends(get_current_user)):
    return mem.get_preferences(user.id)


class PrefPayload(BaseModel):
    key: str
    value: str

@router.put("/preferences")
async def set_preference(payload: PrefPayload, user=Depends(get_current_user)):
    mem.set_preference(user.id, payload.key, payload.value)
    return {"success": True}


# ── WORKSPACE CONTEXT ────────────────────────────────────────────────────────

@router.get("/{agent_id}/context")
async def get_context(agent_id: str, user=Depends(get_current_user)):
    return {"context": mem.get_workspace_context(agent_id, user.id)}


class ContextPayload(BaseModel):
    context: str

@router.put("/{agent_id}/context")
async def update_context(agent_id: str, payload: ContextPayload, user=Depends(get_current_user)):
    mem.set_workspace_context(agent_id, user.id, payload.context)
    return {"success": True}
