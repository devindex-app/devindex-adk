"""Database utilities for saving skill vectors with Supabase."""

import os
from typing import Dict, Optional
from database.db import DatabaseManager
from database.logger import get_db_logger

# Initialize logger immediately when module is imported
logger = get_db_logger("db_utils")
logger.debug("Database utilities module (db_utils.py) imported and logger initialized")


def save_skill_vector_to_db(
    username: str,
    repo_name: str,
    skills: Dict[str, int],
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None
) -> bool:
    """
    Save or update skill vector to database with merge logic.
    
    Merges with existing vector using max(old_score, new_score) for existing skills.
    
    Args:
        username: GitHub username
        repo_name: Repository name that was analyzed
        skills: Dictionary of skills and scores, e.g., {"javascript": 75, "react": 80}
        supabase_url: Supabase project URL (optional, uses SUPABASE_URL env var if not provided)
        supabase_key: Supabase service role key (optional, uses SUPABASE_KEY env var if not provided)
        
    Returns:
        True if successful, False otherwise
    """
    if not skills:
        logger.warning("Empty skills dictionary, skipping database save")
        print("⚠ Warning: Empty skills dictionary, skipping database save")
        return False
    
    if not supabase_url and not os.environ.get("SUPABASE_URL"):
        logger.warning("SUPABASE_URL not set, skipping database save")
        print("⚠ Warning: SUPABASE_URL not set, skipping database save")
        return False
    
    if not supabase_key and not os.environ.get("SUPABASE_KEY"):
        logger.warning("SUPABASE_KEY not set, skipping database save")
        print("⚠ Warning: SUPABASE_KEY not set, skipping database save")
        return False
    
    try:
        logger.info(f"Attempting to save skill vector - Username: {username}, Repo: {repo_name}")
        print(f"\n💾 Attempting to save skill vector to database...")
        print(f"   Username: {username}")
        print(f"   Repo: {repo_name}")
        print(f"   Skills: {len(skills)} skills")
        
        db = DatabaseManager(supabase_url=supabase_url, supabase_key=supabase_key)
        
        # Initialize vocabulary from existing records (if not already done)
        try:
            db.initialize_vocabulary()
            logger.debug("Vocabulary initialized successfully")
        except Exception as vocab_error:
            logger.warning(f"Vocabulary initialization failed (non-critical): {vocab_error}")
            print(f"   ⚠ Vocabulary initialization failed (non-critical): {vocab_error}")
        
        result = db.save_or_update_skill_vector(
            username=username,
            repo_name=repo_name,
            new_skills=skills
        )
        
        record_id = result.get("id") if isinstance(result, dict) else None
        logger.info(f"Successfully saved skill vector! Record ID: {record_id}")
        print(f"   ✓ Successfully saved! Record ID: {record_id}")
        return True
        
    except Exception as e:
        # Log detailed error to file
        logger.error(f"Error saving skill vector to database: {e}", exc_info=True)
        
        # Also print to console
        print(f"\n❌ Error saving skill vector to database:")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}")
        print(f"   📝 Check logs/database_*.log for full details")
        
        # Provide helpful suggestions
        error_str = str(e).lower()
        
        if "supabase_url" in error_str or "supabase_key" in error_str:
            logger.info("Tip: Supabase credentials issue detected")
            print(f"\n   💡 Tip: Check your Supabase environment variables")
            print(f"      Required:")
            print(f"      - SUPABASE_URL: https://<project-ref>.supabase.co")
            print(f"      - SUPABASE_KEY: Service role key from Supabase Dashboard")
            print(f"      Get them from: Supabase Dashboard -> Settings -> API")
        elif "connection" in error_str or "network" in error_str:
            logger.info("Tip: Connection issue detected")
            print(f"\n   💡 Tip: Check your network connection and Supabase URL")
            print(f"      Ensure SUPABASE_URL is correct: https://<project-ref>.supabase.co")
        elif "vector" in error_str or "pgvector" in error_str:
            logger.info("Tip: pgvector extension issue detected")
            print(f"\n   💡 Tip: Ensure pgvector extension is enabled in Supabase")
            print(f"      Run: CREATE EXTENSION IF NOT EXISTS vector;")
        elif "table" in str(e).lower() or "does not exist" in str(e).lower():
            logger.info("Tip: Table does not exist")
            print(f"\n   💡 Tip: Ensure the 'developer_skills' table exists in Supabase")
            print(f"      See database/SUPABASE_SETUP.md for table creation SQL")
        elif "RLS" in str(e) or "row-level" in str(e).lower() or "permission" in error_str:
            logger.info("Tip: RLS (Row Level Security) issue detected")
            print(f"\n   💡 Tip: Row Level Security might be blocking the operation")
            print(f"      Ensure you're using the service_role key (not anon key)")
            print(f"      Or disable RLS: ALTER TABLE developer_skills DISABLE ROW LEVEL SECURITY;")
            print(f"      See database/SUPABASE_SETUP.md for RLS configuration")
        
        return False

