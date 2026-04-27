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
