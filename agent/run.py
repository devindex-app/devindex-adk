"""DevIndex agent entrypoint.

Usage:
    python -m agent.run --username <github_username> --repo <owner/repo>

Outputs a JSON envelope to stdout:
    {"status": "ok", "username": "...", "repo": "...", "skills": {...}, "complexity": 0.42}
    {"status": "error", "error": "...", "error_class": "..."}
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the agents/ project root (one level above agent/)
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)


def _require_env(name: str):
    val = os.environ.get(name, "")
    if not val:
        _fatal(f"Environment variable {name!r} is not set")
    return val


def _fatal(msg: str):
    print(json.dumps({"status": "error", "error": msg, "error_class": "ConfigError"}))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="DevIndex agent — analyse a GitHub repo")
    parser.add_argument("--username", required=True, help="GitHub username")
    parser.add_argument("--repo", required=True, help="Repository (owner/repo or repo)")
    args = parser.parse_args()

    _require_env("GOOGLE_API_KEY")

    # import here (after env is loaded) so modules can read env at import time
    from agent.graph import build_graph

    graph = build_graph()

    initial_state = {
        "username": args.username,
        "repo": args.repo,
        "cache_hit": False,
    }

    final_state = graph.invoke(initial_state)

    if final_state.get("error"):
        print(json.dumps({
            "status": "error",
            "error": final_state["error"],
            "error_class": final_state.get("error_class", "UnknownError"),
        }))
        sys.exit(1)

    skills = final_state.get("validated_skills") or {}
    output = {
        "status": "ok",
        "username": final_state.get("username", args.username),
        "repo": final_state.get("repo_full_name", args.repo),
        "repo_hash": final_state.get("repo_hash", ""),
        "cache_hit": final_state.get("cache_hit", False),
        "complexity": final_state.get("complexity_score", 0.0),
        "skills": skills,
        "files_examined": final_state.get("selected_files", []),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
