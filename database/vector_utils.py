"""Utilities for converting skill dictionaries to vectors and back."""

from typing import Dict, List, Optional, Tuple


# Global skill vocabulary - maps skill names to vector indices
# This should be maintained as skills are discovered
_skill_vocabulary: Dict[str, int] = {}
_vocabulary_lock = False


def get_or_create_skill_index(skill_name: str, max_dimensions: int = 200) -> int:
    """
    Get or create an index for a skill in the vocabulary.
    
    Args:
        skill_name: Name of the skill (e.g., "javascript", "react")
        max_dimensions: Maximum number of dimensions in vector
        
    Returns:
        Index for this skill in the vector
    """
    global _skill_vocabulary
    
    if skill_name not in _skill_vocabulary:
        if len(_skill_vocabulary) >= max_dimensions:
            raise ValueError(f"Maximum skill vocabulary size ({max_dimensions}) reached")
        _skill_vocabulary[skill_name] = len(_skill_vocabulary)
    
    return _skill_vocabulary[skill_name]


def load_vocabulary_from_skills(skills: Dict[str, int], max_dimensions: int = 200):
    """
    Load vocabulary from a skills dictionary.
    This should be called to populate the vocabulary before encoding vectors.
    
    Args:
        skills: Dictionary of skills and scores
        max_dimensions: Maximum number of dimensions
    """
    global _skill_vocabulary
    
    # Add all skills to vocabulary
    for skill_name in skills.keys():
        get_or_create_skill_index(skill_name, max_dimensions)


def skills_to_vector(skills: Dict[str, int], max_dimensions: int = 200) -> List[float]:
    """
    Convert skills dictionary to a normalized vector.
    
    Args:
        skills: Dictionary mapping skill names to scores (0-100)
        max_dimensions: Maximum vector dimensions
        
    Returns:
        Normalized vector as list of floats
    """
    # Load vocabulary from skills
    load_vocabulary_from_skills(skills, max_dimensions)
    
    # Initialize vector with zeros
    vector = [0.0] * max_dimensions
    
    # Fill vector with skill scores
    for skill_name, score in skills.items():
        if skill_name in _skill_vocabulary:
            idx = _skill_vocabulary[skill_name]
            if idx < max_dimensions:
                vector[idx] = float(score) / 100.0  # Normalize to 0-1
    
    return vector


def vector_to_skills(vector: List[float], vocabulary: Optional[Dict[str, int]] = None) -> Dict[str, int]:
    """
    Convert vector back to skills dictionary.
    
    Args:
        vector: Normalized vector (0-1 range)
        vocabulary: Optional vocabulary mapping (if None, uses global)
        
    Returns:
        Dictionary mapping skill names to scores (0-100)
    """
    if vocabulary is None:
        vocabulary = _skill_vocabulary
    
    # Reverse vocabulary: index -> skill_name
    reverse_vocab = {idx: skill_name for skill_name, idx in vocabulary.items()}
    
    skills = {}
    for idx, value in enumerate(vector):
        if idx in reverse_vocab and value > 0:
            # Denormalize back to 0-100 range
            skills[reverse_vocab[idx]] = int(value * 100)
    
    return skills


def merge_skill_vectors(
    old_skills: Dict[str, int],
    new_skills: Dict[str, int]
) -> Dict[str, int]:
    """
    Merge two skill vectors using max(old_score, new_score) for existing skills
    and adding new skills.
    
    Example:
        old: {"javascript": 20, "react": 50}
        new: {"react": 70, "docker": 30}
        result: {"javascript": 20, "react": 70, "docker": 30}
    
    Args:
        old_skills: Existing skill vector
        new_skills: New skill vector from current analysis
        
    Returns:
        Merged skill vector
    """
    merged = old_skills.copy()
    
    for skill_name, new_score in new_skills.items():
        if skill_name in merged:
            # Use max of old and new score
            merged[skill_name] = max(merged[skill_name], new_score)
        else:
            # Add new skill
            merged[skill_name] = new_score
    
    return merged


def build_vocabulary_from_db(skill_jsons: List[Dict[str, int]], max_dimensions: int = 200):
    """
    Build vocabulary from multiple skill JSON objects from database.
    This should be called on startup to load existing skills.
    
    Args:
        skill_jsons: List of skill dictionaries from database
        max_dimensions: Maximum number of dimensions
    """
    global _skill_vocabulary
    
    all_skills = set()
    for skills in skill_jsons:
        if skills:
            all_skills.update(skills.keys())
    
    # Sort for consistent ordering
    sorted_skills = sorted(all_skills)
    
    for skill_name in sorted_skills:
        if len(_skill_vocabulary) < max_dimensions:
            _skill_vocabulary[skill_name] = len(_skill_vocabulary)



