"""Node: look up repo_hash in the repo_cache table."""

import os

from agent.state import AgentState


def check_cache(state: AgentState) -> dict:
    repo_hash = state.get("repo_hash", "")
    repo_full_name = state.get("repo_full_name", "")

    try:
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SECRET_KEY", "") or os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            return {"cache_hit": False, "cached_result": None}

        client = create_client(url, key)

        resp = (
            client.table("repo_cache")
            .select("*")
            .eq("repo_full_name", repo_full_name)
            .eq("repo_hash", repo_hash)
            .limit(1)
            .execute()
        )

        if resp.data:
            row = resp.data[0]
            # bump hit counter
            client.table("repo_cache").update({
                "hits": row.get("hits", 0) + 1,
                "last_hit_at": "now()",
            }).eq("id", row["id"]).execute()
            return {"cache_hit": True, "cached_result": row}

    except Exception:
        pass  # cache miss on any error

    return {"cache_hit": False, "cached_result": None}
