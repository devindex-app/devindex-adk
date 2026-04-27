-- 006_repo_cache.sql
-- The cache that lets us skip the LLM agent when (repo content, prompt, formula, model)
-- all match a previous analysis. UNIQUE constraint encodes the cache key.

CREATE TABLE IF NOT EXISTS public.repo_cache (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  repo_full_name      text NOT NULL,
  repo_hash           text NOT NULL,
  prompt_version      text NOT NULL,
  scoring_version     text NOT NULL,
  model_id            text NOT NULL,

  -- payload
  skill_json          jsonb NOT NULL,
  skill_vector        vector(200),
  complexity          integer,                     -- 0..100, deterministic
  language_bytes      jsonb,                       -- raw GitHub /languages payload
  default_branch_sha  text NOT NULL,
  files_examined      text[] NOT NULL,

  analyzed_at         timestamptz NOT NULL DEFAULT NOW(),
  hits                integer NOT NULL DEFAULT 0,
  last_hit_at         timestamptz,

  UNIQUE (repo_full_name, repo_hash, prompt_version, scoring_version, model_id)
);

ALTER TABLE public.repo_cache ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS repo_cache_public_read ON public.repo_cache;
CREATE POLICY repo_cache_public_read
  ON public.repo_cache FOR SELECT
  USING (true);
