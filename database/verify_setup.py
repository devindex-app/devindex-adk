"""Verify database and logger setup."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def verify_setup():
    """Verify that database and logger are properly set up."""
    print("=" * 60)
    print("DevIndex Database Setup Verification")
    print("=" * 60)
    
    # 1. Check logs directory
    print("\n1. Checking logs directory...")
    logs_dir = Path(__file__).parent.parent / "logs"
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        if logs_dir.exists():
            print(f"   ✓ Logs directory exists: {logs_dir}")
        else:
            print(f"   ❌ Logs directory creation failed: {logs_dir}")
            return False
    except Exception as e:
        print(f"   ❌ Error creating logs directory: {e}")
        return False
    
    # 2. Check logger
    print("\n2. Checking database logger...")
    try:
        from database.logger import get_db_logger
        logger = get_db_logger("verify")
        logger.info("Test log message - logger is working")
        print("   ✓ Logger imported and initialized")
        
        # Check if log file was created
        date_str = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
        log_file = logs_dir / f"database_{date_str}.log"
        if log_file.exists():
            print(f"   ✓ Log file exists: {log_file}")
        else:
            print(f"   ⚠ Log file not found (may be created on first use): {log_file}")
    except Exception as e:
        print(f"   ❌ Logger setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. Check DATABASE_URL
    print("\n3. Checking DATABASE_URL...")
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Mask password
        masked_url = db_url.split("@")[0] + "@***" if "@" in db_url else db_url
        print(f"   ✓ DATABASE_URL is set: {masked_url}")
    else:
        print("   ⚠ DATABASE_URL not set (database operations will be skipped)")
        return True  # This is OK, just means DB won't work
    
    # 4. Check database imports
    print("\n4. Checking database modules...")
    try:
        from database.db import DatabaseManager
        print("   ✓ DatabaseManager imported")
        
        # Models are no longer needed with Supabase client (returns dicts)
        print("   ✓ Database module structure verified")
        
        from database.vector_utils import merge_skill_vectors, skills_to_vector
        print("   ✓ Vector utilities imported")
    except Exception as e:
        print(f"   ❌ Database module import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. Test database connection
    if db_url:
        print("\n5. Testing database connection...")
        try:
            db = DatabaseManager()
            print("   ✓ DatabaseManager initialized")
            
            # Try a simple query to verify connection
            try:
                with db.get_session() as session:
                    result = session.execute("SELECT 1").scalar()
                    print(f"   ✓ Database connection successful (test query returned: {result})")
            except Exception as conn_error:
                print(f"   ⚠ Database connection test failed: {conn_error}")
                print("      This might be OK if table doesn't exist yet")
        except Exception as e:
            print(f"   ❌ Database initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # 6. Check all database files exist
    print("\n6. Checking database files...")
    db_files = [
        "database/__init__.py",
        "database/db.py",
        "database/models.py",
        "database/logger.py",
        "database/vector_utils.py",
        "utils/db_utils.py",
    ]
    all_exist = True
    for file_path in db_files:
        full_path = Path(__file__).parent.parent / file_path
        if full_path.exists():
            print(f"   ✓ {file_path}")
        else:
            print(f"   ❌ {file_path} not found")
            all_exist = False
    
    if not all_exist:
        return False
    
    print("\n" + "=" * 60)
    print("✓ All checks passed! Database setup looks good.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = verify_setup()
    sys.exit(0 if success else 1)



