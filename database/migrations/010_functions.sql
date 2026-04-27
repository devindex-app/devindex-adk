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
