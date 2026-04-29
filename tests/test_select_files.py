import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.nodes.select_files import select_files


def test_select_files_returns_dicts_with_blob_sha():
    """selected_files must be list[dict] with path + blob_sha."""
    state = {
        "file_tree": [
            {"path": "src/main.py", "blob_sha": "sha1"},
            {"path": "README.md", "blob_sha": "sha2"},
            {"path": "src/utils.py", "blob_sha": "sha3"},
        ]
    }
    result = select_files(state)
    selected = result["selected_files"]
    assert isinstance(selected, list)
    assert all(isinstance(f, dict) for f in selected)
    assert all("path" in f and "blob_sha" in f for f in selected)


def test_select_files_preserves_blob_sha():
    state = {
        "file_tree": [{"path": "app.py", "blob_sha": "myblob"}]
    }
    result = select_files(state)
    assert result["selected_files"][0]["blob_sha"] == "myblob"


def test_select_files_caps_at_max_files():
    """Should never return more than 20 files."""
    state = {
        "file_tree": [{"path": f"src/file{i}.py", "blob_sha": f"sha{i}"} for i in range(50)]
    }
    result = select_files(state)
    assert len(result["selected_files"]) <= 20


def test_select_files_skips_node_modules():
    state = {
        "file_tree": [
            {"path": "node_modules/react/index.js", "blob_sha": "badsha"},
            {"path": "src/app.ts", "blob_sha": "goodsha"},
        ]
    }
    result = select_files(state)
    paths = [f["path"] for f in result["selected_files"]]
    assert "node_modules/react/index.js" not in paths
    assert "src/app.ts" in paths
