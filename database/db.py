"""Database connection and session management for Supabase pgvector."""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator, Dict, Optional, List

from database.models import Base, DeveloperSkills
from database.vector_utils import (
    merge_skill_vectors,
    skills_to_vector,
    build_vocabulary_from_db
)
from database.logger import get_db_logger

# Initialize logger immediately when module is imported
logger = get_db_logger("db")
logger.debug("Database module (db.py) imported and logger initialized")


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, database_url: str = None):
        """
        Initialize database manager.
        
        Args:
            database_url: PostgreSQL connection URL.
                         Format: postgresql://user:password@host:port/database
                         If None, reads from DATABASE_URL environment variable.
        """
        if database_url is None:
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                error_msg = "DATABASE_URL environment variable not set"
                logger.error(error_msg)
                raise ValueError(
                    f"{error_msg}. "
                    "Format: postgresql://user:password@host:port/database"
                )
        
        # Convert postgresql:// to postgresql+psycopg:// for psycopg v3 support
        # SQLAlchemy defaults to psycopg2, but we're using psycopg (v3)
        original_url = database_url
        connection_type = "unknown"
        
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
            logger.debug("Converted connection URL to use psycopg (v3) driver")
        elif database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
            logger.debug("Converted postgres:// URL to use psycopg (v3) driver")
        
        # Detect connection type (direct vs pooled)
        # IMPORTANT: Supabase direct connections (port 5432) use IPv6 by default
        # which may not work in WSL2/IPv4-only environments.
        # Pooled connections (port 6543) are IPv4-compatible.
        is_supabase_direct = (
            (":5432/" in original_url or ":5432?" in original_url) and
            ".supabase.co" in original_url
        )
        
        if is_supabase_direct:
            # Automatically convert Supabase direct connection to pooled connection for IPv4 compatibility
            logger.warning(
                "Detected Supabase direct connection (port 5432) - IPv6 may not work in WSL2. "
                "Converting to pooled connection (port 6543) for IPv4 compatibility..."
            )
            
            # For Supabase, the transaction pooler can use the same hostname with port 6543
            # or use aws-0-[region].pooler.supabase.com:6543
            # Let's try changing just the port first (simpler)
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(database_url)
            hostname = parsed.hostname or ""
            
            if "db." in hostname and ".supabase.co" in hostname:
                # For Supabase, we need to change the hostname to the pooled format
                # But we don't know the region. Let's try a simpler approach:
                # Keep same hostname but change port (some Supabase setups support this)
                # OR we could try to construct the pooler hostname, but region is unknown
                
                # Actually, Supabase transaction pooler uses different hostnames per region
                # The safest approach is to just change the port on the same hostname
                # If that doesn't work, user should use the pooled connection string from dashboard
                
                # Replace port 5432 with 6543
                if ":5432/" in database_url:
                    database_url = database_url.replace(":5432/", ":6543/")
                elif ":5432?" in database_url:
                    database_url = database_url.replace(":5432?", ":6543?")
                
                logger.info(f"Converted port 5432 -> 6543 on hostname: {hostname}")
                logger.warning(
                    "Using same hostname with port 6543. If connection fails, use the pooled connection string "
                    "from Supabase dashboard: Settings -> Database -> Connection Pooling -> Transaction mode"
                )
            else:
                # Fallback: just change port
                if ":5432/" in database_url:
                    database_url = database_url.replace(":5432/", ":6543/")
                elif ":5432?" in database_url:
                    database_url = database_url.replace(":5432?", ":6543?")
                logger.info("Converted port 5432 -> 6543 (same hostname)")
            
            connection_type = "pooled (auto-converted from direct)"
        elif ":5432/" in original_url or ":5432?" in original_url:
            connection_type = "direct"
        elif ":6543/" in original_url or ":6543?" in original_url:
            connection_type = "pooled"
        
        # Add connection parameters for Supabase compatibility
        # Supabase requires SSL/TLS connections
        connect_args = {}
        
        # For Supabase, we need to enable SSL
        # psycopg3 uses 'sslmode' parameter
        if "supabase" in database_url.lower():
            connect_args["sslmode"] = "require"
            logger.debug("Added SSL mode 'require' for Supabase connection")
        
        # Try to force IPv4 by adding connection parameters
        # Note: psycopg3 uses 'hostaddr' to force IP, but we can't easily resolve here
        # Instead, we'll rely on the pooled connection conversion above
        
        # Log connection (but mask password)
        masked_url = self._mask_password(database_url)
        logger.info(f"Initializing database connection ({connection_type}): {masked_url}")
        if connect_args:
            logger.debug(f"Connection args: {connect_args}")
        
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,  # Verify connections before using
            echo=False,  # Set to True for SQL debugging (logs to logger)
            connect_args=connect_args if connect_args else {}
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.debug("Database manager initialized successfully")
    
    @staticmethod
    def _mask_password(url: str) -> str:
        """Mask password in database URL for logging."""
        try:
            from urllib.parse import urlparse, urlunparse, parse_qs
            parsed = urlparse(url)
            if parsed.password:
                masked = url.replace(parsed.password, "***")
                return masked
            return url
        except Exception:
            return url.split("@")[0] + "@***" if "@" in url else url
    
    def create_tables(self):
        """
        Create all database tables.
        
        Note: Supabase handles table creation, so this is mainly for local development.
        """
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)."""
        Base.metadata.drop_all(bind=self.engine)
    
    def initialize_vocabulary(self, max_dimensions: int = 100):
        """
        Initialize skill vocabulary from existing database records.
        This should be called on startup to load existing skills.
        
        Args:
            max_dimensions: Maximum vector dimensions
        """
        with self.get_session() as session:
            results = session.query(DeveloperSkills.skill_json).filter(
                DeveloperSkills.skill_json.isnot(None)
            ).all()
            
            skill_jsons = [r[0] for r in results if r[0]]
            build_vocabulary_from_db(skill_jsons, max_dimensions)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        
        Usage:
            with db_manager.get_session() as session:
                # Use session here
                pass
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def save_or_update_skill_vector(
        self,
        username: str,
        repo_name: str,
        new_skills: Dict[str, int],
        max_dimensions: int = 100
    ) -> DeveloperSkills:
        """
        Save or update skill vector for a developer and repository.
        
        Merges with existing vector using max(old_score, new_score) for existing skills
        and adds new skills.
        
        Example:
            Existing: {"javascript": 20, "react": 50}
            New: {"react": 70, "docker": 30}
            Result: {"javascript": 20, "react": 70, "docker": 30}
        
        Args:
            username: GitHub username
            repo_name: Repository name that was analyzed
            new_skills: Dictionary of new skills and scores from current analysis
            max_dimensions: Maximum vector dimensions
            
        Returns:
            DeveloperSkills instance
        """
        logger.info(f"Saving skill vector - Username: {username}, Repo: {repo_name}, Skills: {len(new_skills)}")
        logger.debug(f"New skills: {new_skills}")
        
        with self.get_session() as session:
            try:
                # Try to find existing record for this username and repo
                existing = session.query(DeveloperSkills).filter(
                    DeveloperSkills.username == username,
                    DeveloperSkills.repo_name == repo_name
                ).first()
                
                if existing and existing.skill_json:
                    # Merge with existing: max(old_score, new_score) for existing skills
                    old_skills = existing.skill_json or {}
                    merged_skills = merge_skill_vectors(old_skills, new_skills)
                    logger.info(f"Merging with existing vector - Found {len(old_skills)} existing skills, {len(new_skills)} new skills, {len(merged_skills)} merged")
                    logger.debug(f"Old skills: {old_skills}, New skills: {new_skills}, Merged: {merged_skills}")
                else:
                    # No existing record, use new skills as-is
                    merged_skills = new_skills.copy()
                    logger.info(f"Creating new vector (no existing record found)")
                
                # Convert merged skills to vector
                vector = None
                try:
                    vector = skills_to_vector(merged_skills, max_dimensions)
                    logger.debug(f"Vector created: {len(vector)} dimensions")
                except Exception as vec_error:
                    logger.warning(f"Vector conversion failed: {vec_error}", exc_info=True)
                    # Continue without vector - skill_json is more important
                
                if existing:
                    # Update existing record
                    logger.info(f"Updating existing record (ID: {existing.id})")
                    existing.skill_json = merged_skills
                    if vector is not None:
                        existing.skill_vector = vector
                else:
                    # Create new record
                    logger.info(f"Creating new record")
                    existing = DeveloperSkills(
                        username=username,
                        repo_name=repo_name,
                        skill_json=merged_skills,
                        skill_vector=vector
                    )
                    session.add(existing)
                
                # Flush to get ID before commit
                session.flush()
                logger.info(f"Record flushed, ID: {existing.id}")
                
                # Commit happens automatically when exiting context manager
                session.refresh(existing)
                logger.info(f"✓ Record saved successfully! ID: {existing.id}, Skills: {len(merged_skills)}")
                return existing
                
            except Exception as e:
                logger.error(f"Error in save_or_update_skill_vector: {e}", exc_info=True)
                raise
    
    def get_skill_vector(
        self,
        username: str,
        repo_name: Optional[str] = None
    ) -> Optional[dict]:
        """
        Get skill vector for a developer.
        
        Args:
            username: GitHub username
            repo_name: Optional repository name. If None, returns the first match.
            
        Returns:
            Dictionary with skill vector data, or None if not found
        """
        with self.get_session() as session:
            query = session.query(DeveloperSkills).filter(
                DeveloperSkills.username == username
            )
            
            if repo_name:
                query = query.filter(DeveloperSkills.repo_name == repo_name)
            
            dev_vector = query.first()
            
            if dev_vector:
                return dev_vector.to_dict()
            return None
    
    def get_all_repos_for_user(self, username: str) -> List[dict]:
        """
        Get all skill vectors for a user across all repositories.
        
        Args:
            username: GitHub username
            
        Returns:
            List of skill vector dictionaries
        """
        with self.get_session() as session:
            results = session.query(DeveloperSkills).filter(
                DeveloperSkills.username == username
            ).all()
            
            return [result.to_dict() for result in results]
    
    def search_by_skills(
        self,
        skill_filters: Dict[str, int],
        limit: int = 100,
        repo_name: Optional[str] = None
    ) -> List[dict]:
        """
        Search developers by skills using JSONB queries.
        
        Args:
            skill_filters: Dictionary of skills and minimum scores,
                         e.g., {"react": 50, "javascript": 40}
            limit: Maximum number of results
            repo_name: Optional repository name filter
            
        Returns:
            List of developer skill vectors matching the criteria
        """
        with self.get_session() as session:
            query = session.query(DeveloperSkills)
            
            # Filter by individual skills in skill_json
            for skill_name, min_skill_score in skill_filters.items():
                # JSONB query: skill_json->>'skill_name' extracts the value as text
                # Cast to integer and compare
                query = query.filter(
                    text(f"(skill_json->>'{skill_name}')::int >= :min_score").bindparams(min_score=min_skill_score)
                )
            
            # Optional repository filter
            if repo_name:
                query = query.filter(DeveloperSkills.repo_name == repo_name)
            
            results = query.limit(limit).all()
            return [result.to_dict() for result in results]
    
    def search_by_vector_similarity(
        self,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.5
    ) -> List[dict]:
        """
        Search developers using vector similarity (cosine similarity).
        
        Requires pgvector extension and vector indexes in Supabase.
        
        Args:
            query_vector: Query vector to compare against
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of developer skill vectors sorted by similarity
        """
        with self.get_session() as session:
            # Use pgvector cosine similarity operator
            # Note: This requires pgvector extension and proper indexes
            query = session.query(DeveloperSkills).filter(
                DeveloperSkills.skill_vector.isnot(None)
            ).order_by(
                DeveloperSkills.skill_vector.cosine_distance(query_vector)
            ).limit(limit)
            
            results = query.all()
            return [result.to_dict() for result in results]
    
    def get_all_developers(self, limit: int = 100) -> List[dict]:
        """
        Get all developers with their skill vectors.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of all developer skill vectors
        """
        with self.get_session() as session:
            results = session.query(DeveloperSkills).limit(limit).all()
            return [result.to_dict() for result in results]

