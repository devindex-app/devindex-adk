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

    # --- after fetch_file_tree ---
    file_tree: list   # [{"path": str, "blob_sha": str}, ...]

    # --- after select_files ---
    selected_files: list  # [{"path": str, "blob_sha": str}] ≤20 items

    # --- after check_file_cache ---
    cache_hits: list    # [{"path": str, "skill_json": dict, "complexity": int}]
    cache_misses: list  # [{"path": str, "blob_sha": str}]

    # --- after fetch_files ---
    file_contents: dict   # {path: content_str} — only for cache_misses

    # --- after compute_complexity ---
    complexity_score: float
    complexity_details: dict

    # --- after score_skills ---
    skill_vector: Optional[dict]  # {"skills": [{"name": str, "score": int}]}

    # --- after validate_scores ---
    validated_skills: Optional[dict]  # {name: score (0-100)}

    # --- error tracking ---
    error: Optional[str]
    error_class: Optional[str]
