"""Node: persist analysis results to Supabase.

Writes to three tables:
  file_skill_cache — one row per (repo_full_name, file_path, blob_sha) for each analyzed file
  developer_skills — one row per (username, repo_name), upserted
  repo_cache       — one row per repo, upserted (no longer keyed by commit SHA)
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
    try:
        resp = client.table("skill_vocabulary").select("skill_name, idx").execute()
        return {row["skill_name"]: row["idx"] for row in (resp.data or [])}
    except Exception:
        return {}


def _save_vocabulary(client, vocab: dict[str, int]):
    if not vocab:
        return
    rows = [{"skill_name": name, "idx": idx} for name, idx in vocab.items()]
    try:
        client.table("skill_vocabulary").upsert(rows, on_conflict="skill_name").execute()
    except Exception:
        pass


def _skills_to_vector(skills: dict[str, int], vocab: dict[str, int], max_dim: int = 200) -> list[float]:
    vec = [0.0] * max_dim
    for name, score in skills.items():
        idx = vocab.get(name)
        if idx is not None and idx < max_dim:
            vec[idx] = min(1.0, max(0.0, score / 100.0))
    return vec


def _extend_vocabulary(existing: dict[str, int], new_skills: dict[str, int], max_dim: int = 200) -> dict[str, int]:
    updated = dict(existing)
    for name in sorted(new_skills):
        if name not in updated and len(updated) < max_dim:
            updated[name] = len(updated)
    return updated


def persist(state: AgentState) -> dict:
    username: str = state.get("username", "")
    repo_full_name: str = state.get("repo_full_name", "")
    validated_skills: dict = state.get("validated_skills") or {}
    cache_hits: list = state.get("cache_hits", [])
    cache_misses: list = state.get("cache_misses", [])
    complexity_score: float = state.get("complexity_score", 0.0)

    # When all files were cache hits, validated_skills is empty — aggregate from hits
    if not validated_skills and cache_hits:
        aggregated: dict[str, int] = {}
        for hit in cache_hits:
            for skill, score in (hit.get("skill_json") or {}).items():
                try:
                    aggregated[skill] = max(aggregated.get(skill, 0), int(score))
                except (TypeError, ValueError):
                    pass
        if not aggregated:
            return {}
        validated_skills = aggregated
        # Derive complexity from cached per-file values
        hit_complexities = [h.get("complexity") or 0 for h in cache_hits]
        if hit_complexities:
            complexity_score = sum(hit_complexities) / len(hit_complexities) / 100.0

    if not validated_skills:
        return {}

    try:
        client = _get_client()
    except RuntimeError:
        return {}

    # --- file_skill_cache: persist newly analyzed files ---
    complexity_int = round(complexity_score * 100)
    for file_item in cache_misses:
        try:
            client.table("file_skill_cache").upsert(
                {
                    "repo_full_name": repo_full_name,
                    "file_path": file_item["path"],
                    "blob_sha": file_item["blob_sha"],
                    "skill_json": validated_skills,
                    "complexity": complexity_int,
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="repo_full_name,file_path,blob_sha",
            ).execute()
        except Exception:
            pass  # non-fatal

    # --- vocabulary ---
    vocab = _load_vocabulary(client)
    vocab = _extend_vocabulary(vocab, validated_skills)
    _save_vocabulary(client, vocab)

    skill_vector = _skills_to_vector(validated_skills, vocab)

    now = datetime.now(timezone.utc).isoformat()

    # --- developer_skills upsert ---
    selected_files: list = state.get("selected_files", [])
    files_examined = [f["path"] if isinstance(f, dict) else f for f in selected_files]

    ds_data = {
        "username": username,
        "repo_name": repo_full_name,
        "skill_json": validated_skills,
        "skill_vector": skill_vector,
        "repo_hash": "",  # no longer used as cache key
        "prompt_version": _PROMPT_VERSION,
        "scoring_version": _SCORING_VERSION,
        "model_id": _MODEL_ID,
        "files_examined": files_examined,
        "analyzed_at": now,
        "updated_at": now,
    }

    try:
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
    rc_data = {
        "repo_full_name": repo_full_name,
        "repo_hash": "",  # kept for schema compatibility, no longer a cache key
        "prompt_version": _PROMPT_VERSION,
        "scoring_version": _SCORING_VERSION,
        "model_id": _MODEL_ID,
        "skill_json": validated_skills,
        "complexity": complexity_int,
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
        pass

    return {}
