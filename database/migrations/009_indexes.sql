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
