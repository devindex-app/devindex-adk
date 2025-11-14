"""Database utilities for saving skill vectors with Supabase pgvector."""

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
    database_url: Optional[str] = None
) -> bool:
    """
    Save or update skill vector to database with merge logic.
    
    Merges with existing vector using max(old_score, new_score) for existing skills.
    
    Args:
        username: GitHub username
        repo_name: Repository name that was analyzed
        skills: Dictionary of skills and scores, e.g., {"javascript": 75, "react": 80}
        database_url: Database connection URL (optional, uses DATABASE_URL env var if not provided)
        
    Returns:
        True if successful, False otherwise
    """
    if not skills:
        logger.warning("Empty skills dictionary, skipping database save")
        print("⚠ Warning: Empty skills dictionary, skipping database save")
        return False
    
    if not database_url and not os.environ.get("DATABASE_URL"):
        logger.warning("DATABASE_URL not set, skipping database save")
        print("⚠ Warning: DATABASE_URL not set, skipping database save")
        return False
    
    try:
        logger.info(f"Attempting to save skill vector - Username: {username}, Repo: {repo_name}")
        print(f"\n💾 Attempting to save skill vector to database...")
        print(f"   Username: {username}")
        print(f"   Repo: {repo_name}")
        print(f"   Skills: {len(skills)} skills")
        
        db = DatabaseManager(database_url=database_url)
        
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
        
        logger.info(f"Successfully saved skill vector! Record ID: {result.id}")
        print(f"   ✓ Successfully saved! Record ID: {result.id}")
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
        
        # Check for IPv6/network connection issues
        if ("name or service not known" in error_str or 
            "network is unreachable" in error_str or 
            "ipv6" in error_str or
            "errno -2" in error_str):
            logger.info("Tip: IPv6/Network connectivity issue detected")
            print(f"\n   💡 IPv6/Network Connection Issue Detected")
            print(f"      The direct connection (port 5432) uses IPv6 which may not work in WSL2")
            print(f"      Solution: Use the pooled connection string from Supabase dashboard")
            print(f"      Steps:")
            print(f"        1. Go to Supabase Dashboard -> Settings -> Database")
            print(f"        2. Scroll to 'Connection Pooling' section")
            print(f"        3. Copy the 'Connection string' under 'Transaction' mode")
            print(f"        4. It should look like: postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres")
            print(f"        5. Update your .env file with this DATABASE_URL")
            print(f"      Note: Pooled connections (port 6543) are IPv4-compatible")
        elif "DATABASE_URL" in str(e) or "connection" in error_str:
            logger.info("Tip: DATABASE_URL connection issue detected")
            print(f"\n   💡 Tip: Check your DATABASE_URL environment variable")
            print(f"      It should be in format: postgresql://user:password@host:port/database")
            print(f"      For WSL2/IPv4 environments, use the pooled connection (port 6543)")
        elif "vector" in error_str or "pgvector" in error_str:
            logger.info("Tip: pgvector extension issue detected")
            print(f"\n   💡 Tip: Ensure pgvector extension is enabled in Supabase")
            print(f"      Run: CREATE EXTENSION IF NOT EXISTS vector;")
        elif "table" in str(e).lower() or "does not exist" in str(e).lower():
            logger.info("Tip: Table does not exist")
            print(f"\n   💡 Tip: Ensure the 'developer_skills' table exists in Supabase")
            print(f"      See database/SUPABASE_SETUP.md for table creation SQL")
        elif "RLS" in str(e) or "row-level" in str(e).lower():
            logger.info("Tip: RLS (Row Level Security) issue detected")
            print(f"\n   💡 Tip: Row Level Security might be blocking the operation")
            print(f"      See database/SUPABASE_SETUP.md for RLS configuration")
        
        return False

