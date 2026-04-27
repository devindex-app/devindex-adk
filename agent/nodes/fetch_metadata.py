"""Node: fetch repo details + language bytes from GitHub (2 API calls)."""

from agent.state import AgentState
from tools.github import fetch_repo_details, fetch_repo_languages


def fetch_metadata(state: AgentState) -> dict:
    owner = state["owner"]
    repo_full_name = state["repo_full_name"]
    repo_name = repo_full_name.split("/", 1)[1]

    metadata = fetch_repo_details(owner, repo_name)
    if "error" in metadata:
        return {"error": metadata["error"], "error_class": "GitHubAPIError"}

    languages = fetch_repo_languages(owner, repo_name)
    if isinstance(languages, dict) and "error" in languages:
        languages = {}

    return {
        "repo_metadata": metadata,
        "default_branch": metadata.get("default_branch", "main"),
        "language_bytes": languages,
    }
