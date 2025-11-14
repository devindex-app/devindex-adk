"""Pydantic models for skill vectors."""

from pydantic import BaseModel
from typing import List


class SkillItem(BaseModel):
    """Individual skill with score."""
    name: str
    """Skill name (e.g., 'javascript', 'react', 'docker')."""
    score: int
    """Skill score from 0-100."""


class SkillVector(BaseModel):
    """Skill vector model containing skill scores for a developer."""
    
    username: str
    """GitHub username of the developer."""
    
    skills: List[SkillItem]
    """List of skills with scores.
    Examples: [{'name': 'javascript', 'score': 20}, {'name': 'react', 'score': 80}]
    Skills can include: programming languages, frameworks, tools, technologies, etc.
    """

