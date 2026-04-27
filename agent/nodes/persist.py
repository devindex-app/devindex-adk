"""Node: persist analysis results to Supabase.

Writes to two tables:
  developer_skills — one row per (username, repo_name), upserted
  repo_cache       — one row per (repo_full_name, repo_hash, *_version, model_id)

Vocabulary is also persisted to the DB so vector dimensions are stable across restarts.
"""

import json
import os
from datetime import datetime, timezone

from agent.state import AgentState

_PROMPT_VERSION = os.environ.get("PROMPT_VERSION", "v1")
_SCORING_VERSION = os.environ.get("SCORING_VERSION", "v1")
_MODEL_ID = "gemini-2.5-pro"


def _get_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SECRET_KEY", "") or os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SECRET_KEY not set")
    return create_client(url, key)


def _load_vocabulary(client) -> dict[str, int]:
    """Load skill→index mapping from DB (or return empty dict)."""
    try:
        resp = client.table("skill_vocabulary").select("skill_name, idx").execute()
        return {row["skill_name"]: row["idx"] for row in (resp.data or [])}
    except Exception:
        return {}


def _save_vocabulary(client, vocab: dict[str, int]):
    """Upsert new skill entries into the vocabulary table (best-effort)."""
    if not vocab:
        return
    rows = [{"skill_name": name, "idx": idx} for name, idx in vocab.items()]
    try:
        client.table("skill_vocabulary").upsert(rows, on_conflict="skill_name").execute()
    except Exception:
        pass  # vocabulary table might not exist yet; non-fatal


def _skills_to_vector(skills: dict[str, int], vocab: dict[str, int], max_dim: int = 200) -> list[float]:
    """Convert skills dict to a fixed-dimension normalised vector using the shared vocab."""
    vec = [0.0] * max_dim
    for name, score in skills.items():
        idx = vocab.get(name)
        if idx is not None and idx < max_dim:
            vec[idx] = min(1.0, max(0.0, score / 100.0))
    return vec


def _extend_vocabulary(existing: dict[str, int], new_skills: dict[str, int], max_dim: int = 200) -> dict[str, int]:
    """Add any skills not yet in the vocab and return the extended dict."""
    updated = dict(existing)
    for name in sorted(new_skills):  # sorted → deterministic index assignment
        if name not in updated and len(updated) < max_dim:
            updated[name] = len(updated)
    return updated


def persist(state: AgentState) -> dict:
    username: str = state.get("username", "")
    repo_full_name: str = state.get("repo_full_name", "")
    repo_hash: str = state.get("repo_hash", "")
    validated_skills: dict = state.get("validated_skills") or {}
    selected_files: list = state.get("selected_files", [])
    cache_hit: bool = state.get("cache_hit", False)

    if not validated_skills:
        return {}  # nothing to persist

    try:
        client = _get_client()
    except RuntimeError:
        return {}  # no DB config — skip silently

    # --- vocabulary ---
    vocab = _load_vocabulary(client)
    vocab = _extend_vocabulary(vocab, validated_skills)
    _save_vocabulary(client, vocab)

    skill_vector = _skills_to_vector(validated_skills, vocab)

    now = datetime.now(timezone.utc).isoformat()

    # --- developer_skills upsert ---
    ds_data = {
        "username": username,
        "repo_name": repo_full_name,
        "skill_json": validated_skills,
        "skill_vector": skill_vector,
        "repo_hash": repo_hash,
        "prompt_version": _PROMPT_VERSION,
        "scoring_version": _SCORING_VERSION,
        "model_id": _MODEL_ID,
        "files_examined": selected_files,
        "analyzed_at": now,
        "updated_at": now,
    }

    try:
        # try to get user_id from profiles (optional — may not exist)
        p_resp = (
            client.table("profiles")
            .select("user_id")
            .eq("github_username", username)
            .limit(1)
            .execute()
        )
        if p_resp.data:
            ds_data["user_id"] = p_resp.data[0]["user_id"]
    except Exception:
        pass

    try:
        client.table("developer_skills").upsert(
            ds_data, on_conflict="username,repo_name"
        ).execute()
    except Exception as e:
        return {"error": f"DB write failed: {e}", "error_class": "PersistError"}

    # --- repo_cache upsert ---
    cache_status = "hit" if cache_hit else "fresh"
    rc_data = {
        "repo_full_name": repo_full_name,
        "repo_hash": repo_hash,
        "prompt_version": _PROMPT_VERSION,
        "scoring_version": _SCORING_VERSION,
        "model_id": _MODEL_ID,
        "skill_json": validated_skills,
        "hits": 0,
        "last_hit_at": now,
        "created_at": now,
    }
    try:
        client.table("repo_cache").upsert(
            rc_data,
            on_conflict="repo_full_name,repo_hash,prompt_version,scoring_version,model_id",
        ).execute()
    except Exception:
        pass  # cache write failure is non-fatal

    return {}  # state unchanged — result already in validated_skills
