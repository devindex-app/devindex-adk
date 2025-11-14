# Row Level Security (RLS) Guide for Supabase

## Should You Enable RLS?

**It depends on your use case:**

### ✅ **Disable RLS** (Recommended for DevIndex):
- If you want **public read access** to skill vectors (anyone can query/search)
- If your application handles authentication/authorization at the application layer
- If you want simpler setup and debugging during development

**Disable RLS:**
```sql
ALTER TABLE developer_skills DISABLE ROW LEVEL SECURITY;
```

### 🔒 **Enable RLS** (For Security):
- If you want to restrict who can read/write skill vectors
- If you want database-level security policies
- If different users should see different data

**Enable RLS:**
```sql
ALTER TABLE developer_skills ENABLE ROW LEVEL SECURITY;
```

## RLS Policies for DevIndex

If you decide to enable RLS, here are some common policies:

### Option 1: Public Read, Authenticated Write
```sql
-- Allow anyone to read
CREATE POLICY "Public read access" ON developer_skills
    FOR SELECT
    USING (true);

-- Only authenticated users can write
CREATE POLICY "Authenticated write access" ON developer_skills
    FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Authenticated update access" ON developer_skills
    FOR UPDATE
    USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated delete access" ON developer_skills
    FOR DELETE
    USING (auth.role() = 'authenticated');
```

### Option 2: Public Read and Write (No Restrictions)
```sql
-- Allow anyone to read
CREATE POLICY "Public read" ON developer_skills
    FOR SELECT
    USING (true);

-- Allow anyone to write (for agent/scripts)
CREATE POLICY "Public insert" ON developer_skills
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Public update" ON developer_skills
    FOR UPDATE
    USING (true);

CREATE POLICY "Public delete" ON developer_skills
    FOR DELETE
    USING (true);
```

### Option 3: Service Role Only (Recommended for Agent)
If your agent uses the service role key (not user authentication):

```sql
-- Disable RLS entirely OR
ALTER TABLE developer_skills DISABLE ROW LEVEL SECURITY;

-- OR create a service role policy
CREATE POLICY "Service role full access" ON developer_skills
    FOR ALL
    USING (auth.role() = 'service_role');
```

## Current Status

**Check if RLS is enabled:**
```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'developer_skills';
```

**View existing policies:**
```sql
SELECT * FROM pg_policies WHERE tablename = 'developer_skills';
```

## Recommended Setup for DevIndex

For a developer indexing service where skill vectors should be publicly searchable:

```sql
-- Disable RLS (simplest for public data)
ALTER TABLE developer_skills DISABLE ROW LEVEL SECURITY;
```

**Why?**
- Skill vectors are meant to be discoverable (like LinkedIn profiles)
- No sensitive data (just public GitHub analysis)
- Application layer can handle any needed restrictions
- Easier debugging and troubleshooting

## Troubleshooting RLS Issues

If you get errors like:
```
permission denied for table developer_skills
```

**Solutions:**
1. **Disable RLS** (if you want public access):
   ```sql
   ALTER TABLE developer_skills DISABLE ROW LEVEL SECURITY;
   ```

2. **Check your connection**: Use service role key for agent operations:
   ```
   DATABASE_URL=postgresql://postgres.[ref]:[service-role-key]@...
   ```

3. **Create appropriate policies** (see examples above)

4. **Check logs**: See `logs/database_*.log` for detailed error messages



