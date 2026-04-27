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
