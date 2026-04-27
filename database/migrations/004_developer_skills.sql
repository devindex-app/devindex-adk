-- 004_developer_skills.sql
-- One row per (username, repo). Adds repo_hash + version columns so each row
-- is self-describing for cache decisions; the existing schema lacked these.

CREATE TABLE IF NOT EXISTS public.developer_skills (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username         text NOT NULL,
  repo_name        text NOT NULL,                  -- "owner/repo"
  skill_json       jsonb NOT NULL,                 -- {"javascript": 75, "react": 80, ...}
  skill_vector     vector(200),                    -- sparse, normalised [0..1]
  repo_hash        text NOT NULL,
  prompt_version   text NOT NULL DEFAULT 'v1',
  scoring_version  text NOT NULL DEFAULT 'v1',
  model_id         text NOT NULL,
  files_examined   text[],
  analyzed_at      timestamptz NOT NULL DEFAULT NOW(),
  created_at       timestamptz NOT NULL DEFAULT NOW(),
  updated_at       timestamptz NOT NULL DEFAULT NOW(),
  UNIQUE (username, repo_name)
);

ALTER TABLE public.developer_skills ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS developer_skills_public_read ON public.developer_skills;
CREATE POLICY developer_skills_public_read
  ON public.developer_skills FOR SELECT
  USING (true);
