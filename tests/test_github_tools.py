from unittest.mock import patch
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.github import fetch_repo_file_tree


def test_fetch_repo_file_tree_returns_blobs_only():
    fake_tree_response = {
        "tree": [
            {"type": "blob", "path": "src/main.py", "sha": "abc123"},
            {"type": "tree", "path": "src", "sha": "dir456"},           # dir — skipped
            {"type": "blob", "path": "node_modules/lib.js", "sha": "ign789"},  # ignored dir
            {"type": "blob", "path": "README.md", "sha": "readme11"},
        ],
        "truncated": False,
    }
    with patch("tools.github._get", return_value=fake_tree_response):
        result = fetch_repo_file_tree("owner", "myrepo", "main")

    assert "error" not in result
    paths = [f["path"] for f in result["file_tree"]]
    assert "src/main.py" in paths
    assert "README.md" in paths
    assert "src" not in paths
    assert "node_modules/lib.js" not in paths
    assert result["total_files"] == 2


def test_fetch_repo_file_tree_includes_blob_sha():
    fake_tree_response = {
        "tree": [{"type": "blob", "path": "src/app.py", "sha": "blobsha1"}],
        "truncated": False,
    }
    with patch("tools.github._get", return_value=fake_tree_response):
        result = fetch_repo_file_tree("owner", "myrepo", "main")

    assert result["file_tree"][0] == {"path": "src/app.py", "blob_sha": "blobsha1"}


def test_fetch_repo_file_tree_propagates_api_error():
    with patch("tools.github._get", return_value={"error": "HTTP 404: Not Found"}):
        result = fetch_repo_file_tree("owner", "missing", "main")

    assert "error" in result
