-- VEYRA Agent Memory Schema
-- Run in Supabase SQL editor when ready to enable memory layer

-- Task history — full log of every task an agent has run
create table if not exists agent_task_history (
  id           uuid primary key default gen_random_uuid(),
  agent_id     uuid not null references agents(id) on delete cascade,
  user_id      uuid not null,
  template     text not null,
  task_input   text not null,
  task_output  text not null,
  tokens_used  integer default 0,
  created_at   timestamptz default now()
);

-- Worker notes — persistent scratchpad per agent, readable/writable by the agent
create table if not exists agent_notes (
  id         uuid primary key default gen_random_uuid(),
  agent_id   uuid not null references agents(id) on delete cascade,
  user_id    uuid not null,
  content    text not null default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- User preferences — global key/value context injected into every agent
create table if not exists user_preferences (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null,
  key        text not null,
  value      text not null,
  created_at timestamptz default now(),
  unique(user_id, key)
);

-- Workspace context — per-agent standing brief, always in system prompt
create table if not exists agent_workspace_context (
  id         uuid primary key default gen_random_uuid(),
  agent_id   uuid not null references agents(id) on delete cascade,
  user_id    uuid not null,
  context    text not null default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- RLS: users can only access their own memory
alter table agent_task_history      enable row level security;
alter table agent_notes             enable row level security;
alter table user_preferences        enable row level security;
alter table agent_workspace_context enable row level security;

create policy "user isolation" on agent_task_history      using (user_id = auth.uid());
create policy "user isolation" on agent_notes             using (user_id = auth.uid());
create policy "user isolation" on user_preferences        using (user_id = auth.uid());
create policy "user isolation" on agent_workspace_context using (user_id = auth.uid());
