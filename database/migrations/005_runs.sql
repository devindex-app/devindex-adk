-- 005_runs.sql
-- Audit log of every analysis attempt. Used both as a job queue marker
-- (in_queue / running flags) and as a debugging record.

CREATE TABLE IF NOT EXISTS public.runs (
  id            bigserial PRIMARY KEY,
  username      text NOT NULL,
  repo          text NOT NULL,
  in_queue      boolean DEFAULT true,
  running       boolean DEFAULT false,
  success       boolean,
  output        text,
  error_class   text,
  cache_status  text,                              -- "hit" | "miss" | "stale"
  duration_ms   integer,
  updated_score integer,
  created_at    timestamptz NOT NULL DEFAULT NOW(),
  updated_at    timestamptz NOT NULL DEFAULT NOW()
);

-- runs is internal — no public read.
ALTER TABLE public.runs ENABLE ROW LEVEL SECURITY;
