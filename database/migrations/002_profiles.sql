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
