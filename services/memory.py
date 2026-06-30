from __future__ import annotations
from typing import Any
from services.supabase_client import supabase


# ── TASK HISTORY ─────────────────────────────────────────────────────────────

def save_task(
    *,
    agent_id: str,
    user_id: str,
    template: str,
    task_input: str,
    task_output: str,
    tokens_used: int,
) -> None:
    supabase.table("agent_task_history").insert({
        "agent_id":    agent_id,
        "user_id":     user_id,
        "template":    template,
        "task_input":  task_input,
        "task_output": task_output,
        "tokens_used": tokens_used,
    }).execute()


def get_task_history(agent_id: str, user_id: str, limit: int = 10) -> list[dict]:
    result = (
        supabase.table("agent_task_history")
        .select("task_input, task_output, tokens_used, created_at")
        .eq("agent_id", agent_id)
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


# ── WORKER NOTES ─────────────────────────────────────────────────────────────
# Persistent scratchpad the agent can read and write across tasks.

def get_worker_notes(agent_id: str, user_id: str) -> str:
    result = (
        supabase.table("agent_notes")
        .select("content")
        .eq("agent_id", agent_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0]["content"] if rows else ""


def set_worker_notes(agent_id: str, user_id: str, content: str) -> None:
    existing = (
        supabase.table("agent_notes")
        .select("id")
        .eq("agent_id", agent_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        supabase.table("agent_notes").update({"content": content}).eq(
            "id", existing.data[0]["id"]
        ).execute()
    else:
        supabase.table("agent_notes").insert({
            "agent_id": agent_id,
            "user_id":  user_id,
            "content":  content,
        }).execute()


# ── USER PREFERENCES ─────────────────────────────────────────────────────────
# Key/value store for global user context (tone, domain, output format, etc.)

def get_preferences(user_id: str) -> dict[str, str]:
    result = (
        supabase.table("user_preferences")
        .select("key, value")
        .eq("user_id", user_id)
        .execute()
    )
    return {r["key"]: r["value"] for r in (result.data or [])}


def set_preference(user_id: str, key: str, value: str) -> None:
    existing = (
        supabase.table("user_preferences")
        .select("id")
        .eq("user_id", user_id)
        .eq("key", key)
        .limit(1)
        .execute()
    )
    if existing.data:
        supabase.table("user_preferences").update({"value": value}).eq(
            "id", existing.data[0]["id"]
        ).execute()
    else:
        supabase.table("user_preferences").insert({
            "user_id": user_id,
            "key":     key,
            "value":   value,
        }).execute()


# ── WORKSPACE CONTEXT ────────────────────────────────────────────────────────
# Per-agent standing brief — always injected into the system prompt.

def get_workspace_context(agent_id: str, user_id: str) -> str:
    result = (
        supabase.table("agent_workspace_context")
        .select("context")
        .eq("agent_id", agent_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0]["context"] if rows else ""


def set_workspace_context(agent_id: str, user_id: str, context: str) -> None:
    existing = (
        supabase.table("agent_workspace_context")
        .select("id")
        .eq("agent_id", agent_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        supabase.table("agent_workspace_context").update({"context": context}).eq(
            "id", existing.data[0]["id"]
        ).execute()
    else:
        supabase.table("agent_workspace_context").insert({
            "agent_id": agent_id,
            "user_id":  user_id,
            "context":  context,
        }).execute()


# ── MEMORY PROMPT BUILDER ────────────────────────────────────────────────────
# Assembles all active memory layers into a single string for system prompt injection.

def build_memory_prompt(agent_id: str, user_id: str) -> str:
    sections: list[str] = []

    context = get_workspace_context(agent_id, user_id)
    if context:
        sections.append(f"## Workspace Context\n{context}")

    notes = get_worker_notes(agent_id, user_id)
    if notes:
        sections.append(f"## Worker Notes\n{notes}")

    prefs = get_preferences(user_id)
    if prefs:
        pref_lines = "\n".join(f"- {k}: {v}" for k, v in prefs.items())
        sections.append(f"## User Preferences\n{pref_lines}")

    history = get_task_history(agent_id, user_id, limit=5)
    if history:
        history_lines = "\n\n".join(
            f"Task: {h['task_input'][:200]}\nSummary: {h['task_output'][:300]}"
            for h in reversed(history)
        )
        sections.append(f"## Recent Task History\n{history_lines}")

    if not sections:
        return ""

    return (
        "\n\n---\n## Agent Memory\n"
        + "\n\n".join(sections)
        + "\n---"
    )
