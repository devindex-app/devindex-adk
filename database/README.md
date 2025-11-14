# Database Setup for DevIndex

## Recommended Database: PostgreSQL with JSONB

**Why PostgreSQL + JSONB?**

1. **Dynamic Skills**: Your skill vectors are dynamic - new skills (React, Angular, Unity, etc.) can be added anytime. JSONB allows storing flexible schemas without table migrations.

2. **Efficient Queries**: JSONB supports GIN indexes for fast queries like:
   ```sql
   SELECT * FROM developer_skill_vectors 
   WHERE skills->>'react' >= '50' AND skills->>'javascript' >= '60';
   ```

3. **Already Set Up**: You have `psycopg` and `sqlalchemy` in dependencies.

4. **Future-Proof**: Can add `pgvector` extension later for semantic/vector search if needed.

5. **Production-Ready**: PostgreSQL is battle-tested, ACID-compliant, and scales well.

## Setup Instructions

### 1. Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
```

**macOS:**
```bash
brew install postgresql
```

**Docker (Recommended for Development):**
```bash
docker run --name devindex-db \
  -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_DB=devindex \
  -p 5432:5432 \
  -d postgres:15
```

### 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE devindex;

# Create user (optional)
CREATE USER devindex_user WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE devindex TO devindex_user;
```

### 3. Set Environment Variable

Add to your `.env` file:
```
DATABASE_URL=postgresql://devindex_user:yourpassword@localhost:5432/devindex
```

Or for Docker:
```
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/devindex
```

### 4. Initialize Database Tables

```python
from database.db import DatabaseManager

db = DatabaseManager()
db.create_tables()
```

Or run:
```python
python -c "from database.db import DatabaseManager; DatabaseManager().create_tables()"
```

## Schema

The `developer_skill_vectors` table stores:
- `github_username` (unique): GitHub username
- `skills` (JSONB): `{"javascript": 75, "react": 80, "docker": 40}`
- `analyzed_repo`: Repository that was analyzed
- `created_at`, `updated_at`: Timestamps

## Usage Example

```python
from database.db import DatabaseManager

# Initialize
db = DatabaseManager()

# Save skill vector
skills = {"javascript": 75, "react": 80, "docker": 40}
db.save_skill_vector(
    github_username="jatin-roopchandani",
    skills=skills,
    analyzed_repo="jatin/my-repo"
)

# Retrieve skill vector
skill_vector = db.get_skill_vector("jatin-roopchandani")
print(skill_vector["skills"])  # {"javascript": 75, "react": 80, ...}

# Search developers by skills
results = db.search_by_skills(
    skill_filters={"react": 50, "javascript": 40},
    limit=10
)
```

## Query Examples

PostgreSQL JSONB queries are powerful:

```sql
-- Find developers with React score >= 50
SELECT * FROM developer_skill_vectors 
WHERE (skills->>'react')::int >= 50;

-- Find developers proficient in React OR Vue
SELECT * FROM developer_skill_vectors 
WHERE (skills->>'react')::int >= 60 
   OR (skills->>'vue')::int >= 60;

-- Find developers with multiple skills
SELECT * FROM developer_skill_vectors 
WHERE (skills->>'react')::int >= 50 
  AND (skills->>'javascript')::int >= 40
  AND (skills->>'docker')::int >= 30;
```

## Integration with Agent

The agent generates skill vectors in `ctx.session.state["skill_vector_dict"]`. 
You can save them to the database after analysis completes.



