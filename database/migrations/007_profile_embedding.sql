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
