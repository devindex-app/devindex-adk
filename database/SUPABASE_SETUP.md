# Supabase Setup for DevIndex

## Database Schema

The `developer_skills` table in Supabase should match this schema:

```sql
create table developer_skills (
  id uuid primary key default uuid_generate_v4(),
  username text not null,
  repo_name text not null,
  skill_vector vector(100),  -- 100 = length of your skill vector
  skill_json jsonb,          -- stores human-readable skills
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

## Setup Steps

### 0. RLS (Row Level Security) - Read First!

**For DevIndex, we recommend DISABLING RLS** since skill vectors should be publicly searchable.

```sql
-- Check current RLS status
SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'developer_skills';

-- Disable RLS (recommended for public devIndex)
ALTER TABLE developer_skills DISABLE ROW LEVEL SECURITY;
```

**See `database/RLS_GUIDE.md` for detailed RLS options and policies.**

### 1. Enable pgvector Extension

In your Supabase SQL Editor, run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. Create Indexes (Optional but Recommended)

```sql
-- Index for fast username + repo_name lookups
CREATE INDEX IF NOT EXISTS idx_username_repo ON developer_skills(username, repo_name);

-- GIN index for JSONB queries on skill_json
CREATE INDEX IF NOT EXISTS idx_skill_jsonb ON developer_skills USING gin(skill_json);

-- HNSW index for vector similarity search (optional, for future use)
-- CREATE INDEX IF NOT EXISTS idx_skill_vector ON developer_skills 
-- USING hnsw (skill_vector vector_cosine_ops);
```

### 3. Set Environment Variable

Add your Supabase connection string to `.env`:

```
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

Or use the direct connection (without pooling):

```
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres
```

## How It Works

### Skill Vector Merging

When a skill vector is generated for a repository:

1. **Check if exists**: Look for existing record with `username` + `repo_name`
2. **Merge if exists**: 
   - For existing skills: `new_score = max(old_score, current_score)`
   - For new skills: Add them to the vector
3. **Example**:
   - Existing: `{"javascript": 20, "react": 50}`
   - New: `{"react": 70, "docker": 30}`
   - Result: `{"javascript": 20, "react": 70, "docker": 30}`

### Vector Conversion

- Skills dictionary `{"javascript": 75, "react": 80}` is converted to a normalized vector `[0.75, 0.80, ...]`
- Vector is stored in `skill_vector` column for future similarity searches
- Human-readable JSON is stored in `skill_json` for easy queries

## Usage

```python
from database.db import DatabaseManager

db = DatabaseManager()

# Save/update skill vector (automatically merges if exists)
db.save_or_update_skill_vector(
    username="jatin-roopchandani",
    repo_name="jatin/my-repo",
    new_skills={"javascript": 75, "react": 80, "docker": 40}
)

# Get skill vector for a user and repo
vector = db.get_skill_vector("jatin-roopchandani", "jatin/my-repo")

# Search by skills
results = db.search_by_skills(
    skill_filters={"react": 50, "javascript": 40}
)
```

The agent automatically saves skill vectors after each analysis!

## Logging

All database operations are logged to `logs/database_YYYY-MM-DD.log` for debugging.

Check the logs if you encounter issues:
```bash
tail -f logs/database_$(date +%Y-%m-%d).log
```

