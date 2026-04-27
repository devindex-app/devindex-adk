"""Node: compute the repo-state hash used as the cache key.

Hash inputs (all cheap, no extra API calls beyond what fetch_metadata already did):
  SHA-256(default_branch_sha || sorted_language_bytes || prompt_version || scoring_version || model_id)

We do need one extra API call to get the branch HEAD SHA.
"""

import hashlib
import json
import os

from agent.state import AgentState
from tools.github import fetch_default_branch_sha

_PROMPT_VERSION = os.environ.get("PROMPT_VERSION", "v1")
_SCORING_VERSION = os.environ.get("SCORING_VERSION", "v1")
_MODEL_ID = "gemini-2.5-pro"


def compute_hash(state: AgentState) -> dict:
    owner = state["owner"]
    repo_full_name = state["repo_full_name"]
    repo_name = repo_full_name.split("/", 1)[1]
    branch = state.get("default_branch", "main")
    language_bytes = state.get("language_bytes", {})

    branch_sha = fetch_default_branch_sha(owner, repo_name, branch)

    raw = "|".join([
        branch_sha,
        json.dumps(language_bytes, sort_keys=True),
        _PROMPT_VERSION,
        _SCORING_VERSION,
        _MODEL_ID,
    ])
    repo_hash = hashlib.sha256(raw.encode()).hexdigest()

    return {
        "repo_hash": repo_hash,
        "_branch_sha": branch_sha,   # keep for debugging
    }
