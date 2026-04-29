"""Node: check file_skill_cache for each selected file by (repo, path, blob_sha)."""

import os

from agent.state import AgentState

try:
    from supabase import create_client
except ImportError:
    create_client = None  # type: ignore[assignment]


def check_file_cache(state: AgentState) -> dict:
    repo_full_name = state.get("repo_full_name", "")
    selected_files: list = state.get("selected_files", [])

    if not selected_files:
        return {"cache_hits": [], "cache_misses": []}

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SECRET_KEY", "") or os.environ.get("SUPABASE_KEY", "")

    if not create_client or not url or not key:
        return {"cache_hits": [], "cache_misses": selected_files}

    try:
        client = create_client(url, key)
    except Exception:
        return {"cache_hits": [], "cache_misses": selected_files}

    cache_hits: list = []
    cache_misses: list = []

    for file_item in selected_files:
        path = file_item["path"]
        blob_sha = file_item["blob_sha"]
        try:
            resp = (
                client.table("file_skill_cache")
                .select("skill_json, complexity")
                .eq("repo_full_name", repo_full_name)
                .eq("file_path", path)
                .eq("blob_sha", blob_sha)
                .limit(1)
                .execute()
            )
            if resp.data:
                row = resp.data[0]
                cache_hits.append({
                    "path": path,
                    "skill_json": row.get("skill_json") or {},
                    "complexity": row.get("complexity") or 0,
                })
            else:
                cache_misses.append(file_item)
        except Exception:
            cache_misses.append(file_item)

    return {"cache_hits": cache_hits, "cache_misses": cache_misses}
