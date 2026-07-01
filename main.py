import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import agents, tasks, activity, researcher, agent, terminal, memory

app = FastAPI(title="VEYRA API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router,   prefix="/api/agents",   tags=["agents"])
app.include_router(tasks.router,    prefix="/api/tasks",    tags=["tasks"])
app.include_router(activity.router,    prefix="/api/activity",    tags=["activity"])
app.include_router(researcher.router,  prefix="/api/researcher",  tags=["researcher"])
app.include_router(agent.router,       prefix="/api/agent",       tags=["agent"])
app.include_router(terminal.router,    prefix="/api/terminal",    tags=["terminal"])
app.include_router(memory.router,      prefix="/api/memory",      tags=["memory"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "VEYRA API v1"}
