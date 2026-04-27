"""Node: validate and normalise the username / repo inputs."""

from agent.state import AgentState


def validate_input(state: AgentState) -> dict:
    username: str = state.get("username", "").strip()
    repo: str = state.get("repo", "").strip()

    if not username:
        return {"error": "username is required", "error_class": "ValidationError"}
    if not repo:
        return {"error": "repo is required", "error_class": "ValidationError"}

    if "/" in repo:
        owner, repo_name = repo.split("/", 1)
        repo_full_name = f"{owner}/{repo_name}"
    else:
        owner = username
        repo_full_name = f"{username}/{repo}"

    return {
        "username": username,
        "repo": repo,
        "repo_full_name": repo_full_name,
        "owner": owner,
        "error": None,
        "error_class": None,
    }
