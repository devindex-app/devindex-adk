"""Database models for DevIndex with Supabase pgvector support."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
import uuid

# For pgvector support
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback if pgvector is not installed - will use text type
    from sqlalchemy import TypeDecorator, Text as TextType
    class Vector(TypeDecorator):
        impl = TextType
        cache_ok = True

Base = declarative_base()


class DeveloperSkills(Base):
    """
    Stores skill vectors for developers using Supabase pgvector.
    
    Schema matches Supabase table:
    - id: UUID primary key
    - username: GitHub username
    - repo_name: Repository analyzed
    - skill_vector: Vector(200) for pgvector operations
    - skill_json: JSONB for human-readable skill scores
    """
    __tablename__ = "developer_skills"
    
    # Primary key - UUID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # GitHub username
    username = Column(Text, nullable=False, index=True)
    
    # Repository name
    repo_name = Column(Text, nullable=False, index=True)
    
    # Skill vector for pgvector operations (200 dimensions)
    # Note: Actual vector length depends on total number of skills
    # The vector is a normalized representation of skills
    skill_vector = Column(Vector(200), nullable=True)
    
    # Human-readable skills stored as JSONB: {"javascript": 75, "react": 80}
    skill_json = Column(JSONB, nullable=True, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Composite index on username and repo_name for fast lookups
    __table_args__ = (
        Index('idx_username_repo', 'username', 'repo_name'),
        Index('idx_skill_jsonb', 'skill_json', postgresql_using='gin'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": str(self.id) if self.id else None,
            "username": self.username,
            "repo_name": self.repo_name,
            "skill_json": self.skill_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

