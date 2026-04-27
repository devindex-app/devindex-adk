"""Node: fetch content for each selected file."""

from agent.state import AgentState
from tools.github import fetch_repo_file

_MAX_FILE_BYTES = 80_000  # skip files larger than 80 KB


def fetch_files(state: AgentState) -> dict:
    owner = state["owner"]
    repo_full_name = state["repo_full_name"]
    repo_name = repo_full_name.split("/", 1)[1]
    branch = state.get("default_branch", "main")
    selected = state.get("selected_files", [])

    file_contents: dict[str, str] = {}
    for path in selected:
        result = fetch_repo_file(owner, repo_name, path, branch)
        if "error" in result:
            continue
        content: str = result.get("content", "")
        if len(content.encode()) > _MAX_FILE_BYTES:
            content = content[: _MAX_FILE_BYTES] + "\n... [truncated]"
        file_contents[path] = content

    return {"file_contents": file_contents}
