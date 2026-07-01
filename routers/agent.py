from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from auth import get_current_user
from services.agent_sandbox import run_agent

router = APIRouter()


class AgentRequest(BaseModel):
    task: str
    template: str = "Deep Research Agent"
    agent_id: str = ""


@router.post("/run")
async def launch_agent(payload: AgentRequest, user=Depends(get_current_user)):
    async def stream():
        try:
            async for event in run_agent(
                payload.task,
                template=payload.template,
                agent_id=payload.agent_id,
                user_id=user.id,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
