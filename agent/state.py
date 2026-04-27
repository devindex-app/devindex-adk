"""LangGraph agent state definition."""

from typing import Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # --- inputs ---
    username: str
    repo: str            # "owner/repo" or just "repo"
    repo_full_name: str  # always "owner/repo"
    owner: str

    # --- after fetch_metadata ---
    default_branch: str
    repo_metadata: dict
    language_bytes: dict  # {"Python": 12345, ...}

    # --- after compute_hash ---
    repo_hash: str        # hex digest used as cache key

    # --- after check_cache ---
    cache_hit: bool
    cached_result: Optional[dict]  # None on miss

    # --- after list_files ---
    file_paths: list      # all non-ignored paths

    # --- after select_files ---
    selected_files: list  # ≤20 deterministically chosen paths

    # --- after fetch_files ---
    file_contents: dict   # {path: content}

    # --- after compute_complexity ---
    complexity_score: float
    complexity_details: dict

    # --- after score_skills ---
    skill_vector: Optional[dict]  # raw SkillVector as dict

    # --- after validate_scores ---
    validated_skills: Optional[dict]  # {name: score (0-100)}

    # --- error tracking ---
    error: Optional[str]
    error_class: Optional[str]
