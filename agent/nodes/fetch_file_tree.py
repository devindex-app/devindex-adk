"""Node: fetch file tree with blob SHAs (replaces list_files + compute_hash)."""

from agent.state import AgentState
from tools.github import fetch_repo_file_tree


def fetch_file_tree(state: AgentState) -> dict:
    owner = state["owner"]
    repo_full_name = state["repo_full_name"]
    repo_name = repo_full_name.split("/", 1)[1]
    branch = state.get("default_branch", "main")

    result = fetch_repo_file_tree(owner, repo_name, branch)
    if "error" in result:
        return {"error": str(result["error"]), "error_class": "GitHubAPIError"}

    return {"file_tree": result.get("file_tree", [])}
