"""Database connection and operations using Supabase Python client."""

import os
import time
from datetime import datetime, timezone
from typing import Dict, Optional, List
from supabase import create_client, Client
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
    """Manages database connections and operations using Supabase client."""
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize database manager with Supabase client.
        
        Args:
            supabase_url: Supabase project URL (e.g., https://<project>.supabase.co)
                         If None, reads from SUPABASE_URL environment variable.
            supabase_key: Supabase service role key (for server-side operations)
                         If None, reads from SUPABASE_KEY environment variable.
        """
        if supabase_url is None:
            supabase_url = os.environ.get("SUPABASE_URL")
            if not supabase_url:
                error_msg = "SUPABASE_URL environment variable not set"
                logger.error(error_msg)
                raise ValueError(
                    f"{error_msg}. "
                    "Format: https://<project-ref>.supabase.co"
                )
        
        if supabase_key is None:
            supabase_key = os.environ.get("SUPABASE_KEY")
            if not supabase_key:
                error_msg = "SUPABASE_KEY environment variable not set"
                logger.error(error_msg)
                raise ValueError(
                    f"{error_msg}. "
                    "Get it from Supabase Dashboard -> Settings -> API -> service_role key"
                )
        
        # Create Supabase client
        try:
            self.client: Client = create_client(supabase_url, supabase_key)
            logger.info(f"Initialized Supabase client for: {supabase_url}")
            logger.debug("Supabase client created successfully")
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}", exc_info=True)
            raise
    
    def create_tables(self):
        """
        Note: Supabase handles table creation via SQL Editor.
        This method is kept for compatibility but does nothing.
        See database/SUPABASE_SETUP.md for table creation SQL.
        """
        logger.info("Table creation is handled by Supabase SQL Editor")
        logger.info("See database/SUPABASE_SETUP.md for table creation SQL")
    
    def drop_tables(self):
        """
        Note: Table dropping should be done via Supabase SQL Editor.
        This method is kept for compatibility but does nothing.
        """
        logger.warning("Table dropping should be done via Supabase SQL Editor")
    
    def initialize_vocabulary(self, max_dimensions: int = 200):
        """
        Initialize skill vocabulary from existing database records.
        This should be called on startup to load existing skills.
        
        Args:
            max_dimensions: Maximum vector dimensions
        """
        try:
            # Fetch all records with skill_json
            response = self.client.table("developer_skills").select("skill_json").execute()
            
            skill_jsons = []
            for row in response.data:
                if row.get("skill_json"):
                    skill_jsons.append(row["skill_json"])
            
            build_vocabulary_from_db(skill_jsons, max_dimensions)
            logger.debug(f"Vocabulary initialized from {len(skill_jsons)} records")
        except Exception as e:
            logger.warning(f"Vocabulary initialization failed (non-critical): {e}")
            # Non-critical, so we don't raise
    
    def save_or_update_skill_vector(
        self,
        username: str,
        repo_name: str,
        new_skills: Dict[str, int],
        max_dimensions: int = 200
    ) -> dict:
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
            Dictionary with saved record data (includes 'id' field)
        """
        logger.info(f"Saving skill vector - Username: {username}, Repo: {repo_name}, Skills: {len(new_skills)}")
        logger.debug(f"New skills: {new_skills}")
        
        # Retry logic for transient failures
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                # Try to find existing record
                existing_response = self.client.table("developer_skills").select("*").eq(
                    "username", username
                ).eq("repo_name", repo_name).execute()
                
                existing = existing_response.data[0] if existing_response.data else None
                
                if existing and existing.get("skill_json"):
                    # Merge with existing: max(old_score, new_score) for existing skills
                    old_skills = existing.get("skill_json") or {}
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
                
                # Prepare data for insert/update
                # Note: id, created_at, and updated_at have defaults in the database schema
                # We only need to set updated_at explicitly on UPDATE
                data = {
                    "username": username,
                    "repo_name": repo_name,
                    "skill_json": merged_skills,
                }
                
                if vector is not None:
                    data["skill_vector"] = vector
                
                if existing:
                    # Update existing record
                    # Set updated_at to current timestamp (database default only applies on INSERT)
                    data["updated_at"] = datetime.now(timezone.utc).isoformat()
                    
                    logger.info(f"Updating existing record (ID: {existing.get('id')})")
                    update_response = self.client.table("developer_skills").update(data).eq(
                        "id", existing["id"]
                    ).execute()
                    
                    result = update_response.data[0] if update_response.data else existing
                    logger.info(f"✓ Record updated successfully! ID: {result.get('id')}, Skills: {len(merged_skills)}")
                    return result
                else:
                    # Create new record
                    # id, created_at, and updated_at will use database defaults
                    logger.info(f"Creating new record")
                    insert_response = self.client.table("developer_skills").insert(data).execute()
                    
                    result = insert_response.data[0] if insert_response.data else data
                    logger.info(f"✓ Record created successfully! ID: {result.get('id')}, Skills: {len(merged_skills)}")
                    return result
                    
            except Exception as e:
                error_str = str(e).lower()
                is_retryable = "timeout" in error_str or "connection" in error_str or "network" in error_str
                
                if attempt < max_retries - 1 and is_retryable:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Error on attempt {attempt + 1}/{max_retries}: {e}. "
                        f"Retrying in {wait_time} seconds..."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Error in save_or_update_skill_vector after {attempt + 1} attempts: {e}", exc_info=True)
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
        try:
            query = self.client.table("developer_skills").select("*").eq("username", username)
            
            if repo_name:
                query = query.eq("repo_name", repo_name)
            
            response = query.limit(1).execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting skill vector: {e}", exc_info=True)
            return None
    
    def get_all_repos_for_user(self, username: str) -> List[dict]:
        """
        Get all skill vectors for a user across all repositories.
        
        Args:
            username: GitHub username
            
        Returns:
            List of skill vector dictionaries
        """
        try:
            response = self.client.table("developer_skills").select("*").eq("username", username).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting repos for user: {e}", exc_info=True)
            return []
    
    def search_by_skills(
        self,
        skill_filters: Dict[str, int],
        limit: int = 100,
        repo_name: Optional[str] = None
    ) -> List[dict]:
        """
        Search developers by skills using JSONB queries.
        
        Note: Complex JSONB filtering may require RPC functions in Supabase.
        This implementation fetches records and filters in Python for simplicity.
        
        Args:
            skill_filters: Dictionary of skills and minimum scores,
                         e.g., {"react": 50, "javascript": 40}
            limit: Maximum number of results
            repo_name: Optional repository name filter
            
        Returns:
            List of developer skill vectors matching the criteria
        """
        try:
            # Start with base query
            query = self.client.table("developer_skills").select("*")
            
            # Optional repository filter (simple equality filter)
            if repo_name:
                query = query.eq("repo_name", repo_name)
            
            # Fetch records (PostgREST JSONB filtering is complex, so we filter in Python)
            # For better performance with large datasets, consider creating an RPC function
            response = query.limit(limit * 2).execute()  # Fetch more to account for filtering
            
            # Filter by skills in Python
            filtered_results = []
            for record in response.data or []:
                skill_json = record.get("skill_json") or {}
                matches_all = True
                
                # Check if record matches all skill filters
                for skill_name, min_score in skill_filters.items():
                    skill_value = skill_json.get(skill_name, 0)
                    if not isinstance(skill_value, (int, float)) or skill_value < min_score:
                        matches_all = False
                        break
                
                if matches_all:
                    filtered_results.append(record)
                    if len(filtered_results) >= limit:
                        break
            
            return filtered_results
        except Exception as e:
            logger.error(f"Error searching by skills: {e}", exc_info=True)
            return []
    
    def search_by_vector_similarity(
        self,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.5
    ) -> List[dict]:
        """
        Search developers using vector similarity (cosine similarity).
        
        Requires pgvector extension and vector indexes in Supabase.
        Note: This requires using RPC functions in Supabase for vector similarity search.
        
        Args:
            query_vector: Query vector to compare against
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of developer skill vectors sorted by similarity
        """
        try:
            # For vector similarity, we need to use a Postgres function
            # This is a simplified version - you may need to create a function in Supabase
            # that performs the vector similarity search
            logger.warning("Vector similarity search requires custom Postgres function")
            logger.warning("This feature needs to be implemented with a Supabase RPC function")
            
            # For now, return empty list
            # TODO: Implement with Supabase RPC function for vector similarity
            return []
        except Exception as e:
            logger.error(f"Error in vector similarity search: {e}", exc_info=True)
            return []
    
    def get_all_developers(self, limit: int = 100) -> List[dict]:
        """
        Get all developers with their skill vectors.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of all developer skill vectors
        """
        try:
            response = self.client.table("developer_skills").select("*").limit(limit).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting all developers: {e}", exc_info=True)
            return []
