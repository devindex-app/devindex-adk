-- 011_skill_vocabulary.sql
-- Persists the skill→vector-index mapping so all processes share the same
-- vocabulary and vector dimensions remain stable across restarts.

CREATE TABLE IF NOT EXISTS public.skill_vocabulary (
  skill_name  text PRIMARY KEY,
  idx         integer NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT NOW()
);

-- Unique index on idx to prevent two skills sharing the same dimension
CREATE UNIQUE INDEX IF NOT EXISTS skill_vocabulary_idx_unique
  ON public.skill_vocabulary (idx);

ALTER TABLE public.skill_vocabulary ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS skill_vocabulary_public_read ON public.skill_vocabulary;
CREATE POLICY skill_vocabulary_public_read
  ON public.skill_vocabulary FOR SELECT
  USING (true);
