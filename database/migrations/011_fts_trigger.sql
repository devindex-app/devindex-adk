-- 011_fts_trigger.sql
-- Auto-populate fts_doc from source_text on every insert/update to profile_embedding.

CREATE OR REPLACE FUNCTION public.profile_embedding_set_fts()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.fts_doc := to_tsvector('english', COALESCE(NEW.source_text, ''));
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_profile_embedding_fts ON public.profile_embedding;
CREATE TRIGGER trg_profile_embedding_fts
  BEFORE INSERT OR UPDATE ON public.profile_embedding
  FOR EACH ROW EXECUTE FUNCTION public.profile_embedding_set_fts();
