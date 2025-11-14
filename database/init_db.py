"""Initialize database tables for Supabase."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from database.db import DatabaseManager


def main():
    """
    Create database tables.
    
    Note: For Supabase, tables are typically created via SQL Editor.
    This script is mainly for local development/testing.
    """
    if not os.environ.get("DATABASE_URL"):
        print("❌ DATABASE_URL environment variable not set.")
        print("Please set it in your .env file:")
        print("DATABASE_URL=postgresql://user:password@host:port/database")
        sys.exit(1)
    
    try:
        print("Initializing database...")
        print("Note: For Supabase, ensure the table is created via SQL Editor first!")
        print("See database/SUPABASE_SETUP.md for details.\n")
        
        db = DatabaseManager()
        db.create_tables()
        print("✓ Database tables created successfully!")
        print("\nTables created:")
        print("  - developer_skills")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

