-- 001_extensions.sql
-- Enables the Postgres extensions DevIndex relies on.
-- Already run manually by the project owner before the rest of these migrations.
-- Keeping the file here so re-creating the project from scratch is one command.

CREATE EXTENSION IF NOT EXISTS vector;        -- pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- trigram fuzzy match for usernames
CREATE EXTENSION IF NOT EXISTS pgcrypto;      -- gen_random_uuid()
