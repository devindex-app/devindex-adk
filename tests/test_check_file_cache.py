import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch


def _mock_client_with_row(row_data):
    """Return a mock Supabase client that returns row_data for a .execute() call."""
    mock_exec = MagicMock()
    mock_exec.data = row_data
    chain = MagicMock()
    chain.execute.return_value = mock_exec
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value = chain
    return mock_client


def test_check_file_cache_hit():
    from agent.nodes.check_file_cache import check_file_cache

    mock_client = _mock_client_with_row([{"skill_json": {"python": 80}, "complexity": 60}])

    with patch("agent.nodes.check_file_cache.os") as mock_os, \
         patch("agent.nodes.check_file_cache.create_client", return_value=mock_client):
        mock_os.environ.get.side_effect = lambda k, d="": "val" if k in ("SUPABASE_URL", "SUPABASE_SECRET_KEY") else d
        result = check_file_cache({
            "repo_full_name": "jatin/myapp",
            "selected_files": [{"path": "src/main.py", "blob_sha": "abc123"}],
        })

    assert result["cache_hits"] == [{"path": "src/main.py", "skill_json": {"python": 80}, "complexity": 60}]
    assert result["cache_misses"] == []


def test_check_file_cache_miss():
    from agent.nodes.check_file_cache import check_file_cache

    mock_client = _mock_client_with_row([])  # empty = miss

    with patch("agent.nodes.check_file_cache.os") as mock_os, \
         patch("agent.nodes.check_file_cache.create_client", return_value=mock_client):
        mock_os.environ.get.side_effect = lambda k, d="": "val" if k in ("SUPABASE_URL", "SUPABASE_SECRET_KEY") else d
        result = check_file_cache({
            "repo_full_name": "jatin/myapp",
            "selected_files": [{"path": "src/main.py", "blob_sha": "abc123"}],
        })

    assert result["cache_hits"] == []
    assert result["cache_misses"] == [{"path": "src/main.py", "blob_sha": "abc123"}]


def test_check_file_cache_no_creds_treats_all_as_misses():
    """Without DB credentials, all files are treated as cache misses."""
    from agent.nodes.check_file_cache import check_file_cache

    result = check_file_cache({
        "repo_full_name": "jatin/myapp",
        "selected_files": [{"path": "src/main.py", "blob_sha": "abc123"}],
    })

    assert result["cache_hits"] == []
    assert result["cache_misses"] == [{"path": "src/main.py", "blob_sha": "abc123"}]


def test_check_file_cache_empty_selected_files():
    from agent.nodes.check_file_cache import check_file_cache

    result = check_file_cache({"repo_full_name": "jatin/myapp", "selected_files": []})

    assert result["cache_hits"] == []
    assert result["cache_misses"] == []
