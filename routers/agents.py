from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from models.schemas import AgentCreate
from services.supabase_client import supabase

router = APIRouter()


@router.post("")
async def deploy_agent(payload: AgentCreate, user=Depends(get_current_user)):
    data = {
        "user_id": user.id,
        "name": payload.name,
        "template": payload.template,
        "model": payload.model,
        "mission_goal": payload.mission_goal,
        "status": "active",
    }
    result = supabase.table("agents").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create agent")

    agent = result.data[0]
    supabase.table("activity_logs").insert({
        "user_id": user.id,
        "agent_id": agent["id"],
        "agent_name": agent["name"],
        "event_type": "agent_deployed",
        "message": f"{agent['name']} deployed and ready",
    }).execute()

    return agent


@router.get("")
async def list_agents(user=Depends(get_current_user)):
    result = (
        supabase.table("agents")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


@router.get("/stats")
async def get_stats(user=Depends(get_current_user)):
    agents = supabase.table("agents").select("*").eq("user_id", user.id).execute()
    tasks = supabase.table("tasks").select("*").eq("user_id", user.id).execute()
    activity = (
        supabase.table("activity_logs")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    agent_list = agents.data or []
    task_list = tasks.data or []

    return {
        "agents_online": len([a for a in agent_list if a["status"] == "active"]),
        "agents_total": len(agent_list),
        "tasks_completed": len([t for t in task_list if t["status"] == "completed"]),
        "tasks_running": len([t for t in task_list if t["status"] == "running"]),
        "recent_activity": activity.data or [],
    }


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, user=Depends(get_current_user)):
    supabase.table("agents").delete().eq("id", agent_id).eq("user_id", user.id).execute()
    return {"success": True}
