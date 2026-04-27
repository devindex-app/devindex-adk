"""Node: fetch all file paths from the repo using the Git Trees API (1 call)."""

from agent.state import AgentState
from tools.github import fetch_repo_file_paths


def list_files(state: AgentState) -> dict:
    owner = state["owner"]
    repo_full_name = state["repo_full_name"]
    repo_name = repo_full_name.split("/", 1)[1]
    branch = state.get("default_branch", "main")

    result = fetch_repo_file_paths(owner, repo_name, branch)
    if "error" in result:
        return {"error": result["error"], "error_class": "GitHubAPIError"}

    return {"file_paths": result.get("file_paths", [])}
