# VEYRA Runtime

Agent execution engine powering the VEYRA platform.

## Stack

- **FastAPI** — async Python API
- **Anthropic Claude** — agent reasoning and tool use
- **E2B** — isolated cloud sandboxes for code execution
- **Supabase** — auth and persistence

## Setup

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn main:app --reload
```

## Structure

```
main.py              # FastAPI entry point
auth.py              # Supabase JWT middleware
routers/             # API route handlers
services/            # Agent execution, Claude integration
models/              # Pydantic schemas
```
