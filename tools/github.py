"""GitHub REST API tools — pure functions, no shell or git CLI."""

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Optional

_BASE_URL = "https://api.github.com"

_IGNORED_DIRS = {
    "node_modules", ".git", ".svn", ".hg", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".venv", "venv", "env", "dist", "build", ".next",
    ".nuxt", ".cache", "coverage", ".nyc_output", ".idea", ".vscode",
    "target", "out", "bin", "obj", ".gradle", ".mvn", "vendor",
    "bower_components", ".sass-cache", ".parcel-cache",
}

_IGNORED_SUFFIXES = (".pyc", ".pyo", ".pyd", ".class", ".o", ".so", ".dll")


def _headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    h = {"Accept": "application/vnd.github.v3+json"}
    # only use the token if it looks real (not a placeholder like "ghp_...")
    if token and not token.endswith("...") and len(token) > 10:
        h["Authorization"] = f"token {token}"
    return h


def _get(endpoint: str) -> dict | list:
    url = f"{_BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "status_code": e.code}
    except Exception as e:
        return {"error": str(e)}


def fetch_repo_details(owner: str, repo: str) -> dict:
    """Return name, full_name, description, default_branch, language, stars, forks, topics."""
    data = _get(f"/repos/{owner}/{repo}")
    if "error" in data:
        return data
    return {
        "name": data.get("name", ""),
        "full_name": data.get("full_name", ""),
        "description": data.get("description", ""),
        "language": data.get("language", ""),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "created_at": data.get("created_at", ""),
        "pushed_at": data.get("pushed_at", ""),
        "size": data.get("size", 0),
        "default_branch": data.get("default_branch", "main"),
        "topics": data.get("topics", []),
        "is_fork": data.get("fork", False),
        "archived": data.get("archived", False),
    }


def fetch_repo_languages(owner: str, repo: str) -> dict:
    """Return {language: bytes_count} for the repo."""
    data = _get(f"/repos/{owner}/{repo}/languages")
    if isinstance(data, dict) and "error" in data:
        return data
    return data  # already {lang: bytes}


def fetch_default_branch_sha(owner: str, repo: str, branch: str) -> str:
    """Return the HEAD commit SHA of a branch — used for the repo-state hash."""
    data = _get(f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
    if "error" in data:
        return ""
    return data.get("object", {}).get("sha", "")


def fetch_repo_file_paths(owner: str, repo: str, branch: str) -> dict:
    """
    Return all file paths in the repo using the Git Trees API (single call).
    Ignores common build / dependency directories.
    """
    data = _get(f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
    if "error" in data:
        return data

    all_files = []
    for item in data.get("tree", []):
        if item.get("type") != "blob":
            continue
        path: str = item.get("path", "")
        parts = path.split("/")
        # drop if any dir component is in the ignore list
        if any(p in _IGNORED_DIRS for p in parts[:-1]):
            continue
        if path.endswith(_IGNORED_SUFFIXES):
            continue
        all_files.append(path)

    return {
        "repo": f"{owner}/{repo}",
        "branch": branch,
        "total_files": len(all_files),
        "file_paths": sorted(all_files),
        "truncated": data.get("truncated", False),
    }


def fetch_repo_file_tree(owner: str, repo: str, branch: str) -> dict:
    """
    Return all file paths with their blob SHAs using the Git Trees API.
    Used for file-level cache invalidation: if blob_sha is unchanged since
    the last analysis, the cached score for that file is reused.
    """
    data = _get(f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
    if "error" in data:
        return data

    file_tree = []
    for item in data.get("tree", []):
        if item.get("type") != "blob":
            continue
        path: str = item.get("path", "")
        parts = path.split("/")
        if any(p in _IGNORED_DIRS for p in parts[:-1]):
            continue
        if path.endswith(_IGNORED_SUFFIXES):
            continue
        file_tree.append({"path": path, "blob_sha": item.get("sha", "")})

    return {
        "repo": f"{owner}/{repo}",
        "branch": branch,
        "total_files": len(file_tree),
        "file_tree": file_tree,
        "truncated": data.get("truncated", False),
    }


def fetch_repo_file(owner: str, repo: str, file_path: str, branch: str) -> dict:
    """Fetch the decoded content of a single file."""
    data = _get(f"/repos/{owner}/{repo}/contents/{file_path}?ref={branch}")
    if isinstance(data, dict) and "error" in data:
        return data
    if isinstance(data, list):
        return {"error": f"{file_path} is a directory, not a file"}
    if data.get("type") != "file":
        return {"error": f"{file_path} is not a file"}

    content = ""
    if data.get("encoding") == "base64":
        try:
            content = base64.b64decode(data.get("content", "")).decode("utf-8")
        except UnicodeDecodeError:
            return {"error": f"{file_path} is binary"}
        except Exception as e:
            return {"error": str(e)}
    else:
        content = data.get("content", "")

    return {
        "path": data.get("path", ""),
        "size": data.get("size", 0),
        "sha": data.get("sha", ""),
        "content": content,
    }
