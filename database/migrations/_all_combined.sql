
-- ===== 001_extensions.sql =====

-- 001_extensions.sql
-- Enables the Postgres extensions DevIndex relies on.
-- Already run manually by the project owner before the rest of these migrations.
-- Keeping the file here so re-creating the project from scratch is one command.

CREATE EXTENSION IF NOT EXISTS vector;        -- pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- trigram fuzzy match for usernames
CREATE EXTENSION IF NOT EXISTS pgcrypto;      -- gen_random_uuid()

-- ===== 002_profiles.sql =====

-- 002_profiles.sql
-- The profiles table mirrors the shape the existing frontend already expects
-- (see frontend/src/integrations/supabase/types.ts). Custom-auth fields are
-- preserved; we are not migrating to Supabase Auth in this iteration.

CREATE TABLE IF NOT EXISTS public.profiles (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id              uuid UNIQUE NOT NULL DEFAULT gen_random_uuid(),
  username             text UNIQUE,
  full_name            text,
  email                text UNIQUE,
  email_verified       boolean DEFAULT false,
  password_hash        text,
  avatar_url           text,
  bio                  text,
  location             text,

  github_username      text,
  github_score         integer,
  leetcode_username    text,
  leetcode_score       integer,
  codeforces_username  text,
  codeforces_score     integer,
  overall_rank         integer,

  skills               text[],
  badges               text[],

  -- auth bookkeeping
  verified             boolean DEFAULT false,
  verification_token   text,
  reset_token          text,
  reset_token_expires  timestamptz,
  login_attempts       integer DEFAULT 0,
  locked_until         timestamptz,
  last_login           timestamptz,
  provider_id          text,

  created_at           timestamptz NOT NULL DEFAULT NOW(),
  updated_at           timestamptz NOT NULL DEFAULT NOW()
);

-- RLS: public read (it's a leaderboard), writes only via secret key.
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS profiles_public_read ON public.profiles;
CREATE POLICY profiles_public_read
  ON public.profiles FOR SELECT
  USING (true);

-- ===== 003_connected_repositories.sql =====

-- 003_connected_repositories.sql
-- Repos a user has linked to their DevIndex profile.

CREATE TABLE IF NOT EXISTS public.connected_repositories (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
  github_username  text NOT NULL,
  repo_id          bigint NOT NULL,
  repo_name        text NOT NULL,
  repo_full_name   text NOT NULL,
  description      text,
  language         text,
  stargazers_count integer DEFAULT 0,
  forks_count      integer DEFAULT 0,
  html_url         text NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT NOW(),
  updated_at       timestamptz NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, repo_id)
);

ALTER TABLE public.connected_repositories ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS connected_repositories_public_read ON public.connected_repositories;
CREATE POLICY connected_repositories_public_read
  ON public.connected_repositories FOR SELECT
  USING (true);

-- ===== 004_developer_skills.sql =====

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

-- ===== 005_runs.sql =====

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

-- ===== 006_repo_cache.sql =====

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

-- ===== 007_profile_embedding.sql =====

-- 007_profile_embedding.sql
-- Per-developer embedding for semantic search. Dimension is locked at
-- create time and must match the EMBEDDING_MODEL in the backend env.
-- Defaulting to 768 (Gemini text-embedding-004). If we switch to OpenAI
-- text-embedding-3-small we will need a separate migration to recreate
-- the column at vector(1536) and rebuild the IVFFLAT index.

CREATE TABLE IF NOT EXISTS public.profile_embedding (
  username         text PRIMARY KEY,
  embedding        vector(768) NOT NULL,
  source_text      text NOT NULL,
  embedding_model  text NOT NULL,
  fts_doc          tsvector,
  updated_at       timestamptz NOT NULL DEFAULT NOW()
);

ALTER TABLE public.profile_embedding ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS profile_embedding_public_read ON public.profile_embedding;
CREATE POLICY profile_embedding_public_read
  ON public.profile_embedding FOR SELECT
  USING (true);

-- ===== 008_match_audit.sql =====

-- 008_match_audit.sql
-- Records every job-description → ranked-candidates response so we can
-- detect score drift after a model bump. Internal table, not exposed publicly.

CREATE TABLE IF NOT EXISTS public.match_audit (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  jd_text          text NOT NULL,
  jd_hash          text NOT NULL,
  candidates       jsonb NOT NULL,
  weights          jsonb NOT NULL,
  embedding_model  text NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT NOW()
);

ALTER TABLE public.match_audit ENABLE ROW LEVEL SECURITY;
-- No public read policy: secret-key only.

-- ===== 009_indexes.sql =====

-- 009_indexes.sql
-- All indexes in one place so the planner picks the right ones from day one.
-- IVFFLAT indexes are fine on small tables; once we cross ~10k rows we may
-- want to reindex with HNSW (Supabase pgvector >= 0.7).

-- profiles
CREATE INDEX IF NOT EXISTS idx_profiles_username
  ON public.profiles (lower(username));
CREATE INDEX IF NOT EXISTS idx_profiles_username_trgm
  ON public.profiles USING GIN (username gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_profiles_score
  ON public.profiles (github_score DESC NULLS LAST);

-- developer_skills
CREATE INDEX IF NOT EXISTS idx_dev_skills_username
  ON public.developer_skills (username);
CREATE INDEX IF NOT EXISTS idx_dev_skills_skills_gin
  ON public.developer_skills USING GIN (skill_json);
CREATE INDEX IF NOT EXISTS idx_dev_skills_vector
  ON public.developer_skills USING ivfflat (skill_vector vector_cosine_ops)
  WITH (lists = 50);

-- connected_repositories
CREATE INDEX IF NOT EXISTS idx_conn_repos_user
  ON public.connected_repositories (user_id);
CREATE INDEX IF NOT EXISTS idx_conn_repos_full_name
  ON public.connected_repositories (repo_full_name);

-- runs
CREATE INDEX IF NOT EXISTS idx_runs_username_created
  ON public.runs (username, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_in_progress
  ON public.runs (in_queue, running)
  WHERE in_queue OR running;

-- repo_cache
CREATE INDEX IF NOT EXISTS idx_repo_cache_lookup
  ON public.repo_cache (repo_full_name, prompt_version, scoring_version);

-- profile_embedding
CREATE INDEX IF NOT EXISTS idx_profile_embedding_ann
  ON public.profile_embedding USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_profile_embedding_fts
  ON public.profile_embedding USING GIN (fts_doc);

-- match_audit
CREATE INDEX IF NOT EXISTS idx_match_audit_jd_hash
  ON public.match_audit (jd_hash);

-- ===== 010_functions.sql =====

-- 010_functions.sql
-- RPCs the backend calls. Kept STABLE / SECURITY INVOKER so RLS still applies.

-- search_developers: hybrid semantic + lexical search.
--   alpha = 1.0 → pure cosine, 0.0 → pure tsvector. Default 0.7 favours semantics.
CREATE OR REPLACE FUNCTION public.search_developers(
  query_text       text,
  query_embedding  vector(768),
  match_count      int   DEFAULT 20,
  alpha            float DEFAULT 0.7
) RETURNS TABLE (
  username      text,
  cosine_sim    float,
  lexical_rank  float,
  combined      float
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    pe.username,
    (1 - (pe.embedding <=> query_embedding))::float                                AS cosine_sim,
    COALESCE(ts_rank_cd(pe.fts_doc, plainto_tsquery('english', query_text)), 0)    AS lexical_rank,
    (alpha * (1 - (pe.embedding <=> query_embedding))
       + (1 - alpha) * COALESCE(ts_rank_cd(pe.fts_doc, plainto_tsquery('english', query_text)), 0))::float
                                                                                   AS combined
  FROM public.profile_embedding pe
  ORDER BY combined DESC,
           pe.username ASC                          -- deterministic tiebreak
  LIMIT match_count;
$$;

-- set_user_context: present in the legacy types.ts file, kept here as a
-- no-op stub so the generated TypeScript types continue to compile if the
-- frontend regenerates them.
CREATE OR REPLACE FUNCTION public.set_user_context(user_id uuid)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  PERFORM set_config('request.user_id', user_id::text, true);
END;
$$;
