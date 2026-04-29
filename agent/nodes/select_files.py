"""Node: deterministically select ≤40 representative files.

Algorithm (reproducible given the same file list):
1. Score every file by name importance + extension priority.
2. Sort by (score desc, depth asc, path asc).
3. Take the top MAX_FILES, capping any single directory at DIR_CAP files
   to avoid over-weighting monolithic folders.

Name-based scoring is layered on top of extension scoring so that
e.g. `auth/router.py` (core name + good extension) outranks
`utils/constants.py` (utility name + same extension).
"""

from agent.state import AgentState

MAX_FILES = 40
DIR_CAP   = 8   # raised from 5 to accommodate larger repos at 40 files

# ── Extension priority (base score) ─────────────────────────────────────────
_EXT_PRIORITY: dict[str, int] = {
    ".py": 10, ".ts": 10, ".tsx": 10, ".go": 10, ".rs": 10,
    ".java": 10, ".kt": 10, ".cpp": 10, ".cc": 10, ".cxx": 10,
    ".c": 9,  ".cs": 9,  ".rb": 9,  ".swift": 9,
    ".js": 8,  ".jsx": 8, ".vue": 8,  ".svelte": 8,
    ".tf": 7,  ".bicep": 7,
    "dockerfile": 7,
    ".yaml": 6, ".yml": 6, ".toml": 6,
    ".json": 5,
    ".html": 3, ".css": 3, ".scss": 3,
    ".md": 1,  ".txt": 1, ".rst": 1,
}

# ── Name-based boosts (applied to the stem, case-insensitive) ───────────────
# +5 → entry-points and core architectural files
_BOOST_HIGH = {
    "main", "app", "application", "server", "index",
    "api", "router", "routes", "route",
    "model", "models", "schema", "schemas",
    "auth", "authentication", "authorization",
    "core", "engine", "agent", "pipeline",
    "service", "services",
    "controller", "controllers",
    "handler", "handlers",
    "database", "db", "store", "repository", "repo",
    "graph", "workflow",
    "config", "settings", "env",
}

# +2 → supporting but still interesting files
_BOOST_MED = {
    "middleware", "interceptor",
    "client", "connection",
    "types", "interfaces", "base", "abstract",
    "utils", "helpers", "common", "shared",
    "security", "permissions", "roles",
    "serializer", "serializers", "validator", "validators",
    "factory", "builder",
    "queue", "worker", "task", "job",
    "cache", "session",
    "embed", "embedding", "vector",
}

# −3 → files unlikely to reveal real skill signal
_DEMOTE = {
    "__init__", "conftest", "setup", "manage", "wsgi", "asgi",
    "seed", "fixture", "fixtures",
    "migration", "migrations",
    "changelog", "license", "contributing", "readme",
    "mock", "mocks", "stub", "stubs", "fake",
    "constants", "constant",
}

_SKIP_NAMES    = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock"}
_SKIP_SUFFIXES = (".min.js", ".min.css", ".bundle.js", ".map", ".lock", ".sum")

_IGNORED_DIRS = {
    "node_modules", "dist", "build", ".git", "__pycache__", "vendor",
    "venv", ".venv", "coverage", ".next", ".nuxt", "target", "out",
}


def _score(path: str) -> int:
    lower = path.lower()
    parts = lower.split("/")
    name  = parts[-1]

    if any(p in _IGNORED_DIRS for p in parts[:-1]):
        return -1
    if name in _SKIP_NAMES:
        return -1
    if any(lower.endswith(s) for s in _SKIP_SUFFIXES):
        return -1
    if "generated" in lower or ".g." in lower or "autogen" in lower:
        return -1

    # base score from extension
    base = 4  # unknown extension fallback
    for key, pri in _EXT_PRIORITY.items():
        if lower.endswith(key) or key in lower:
            base = pri
            break

    # stem = filename without extension(s), e.g. "auth.service" → "auth"
    stem = name.split(".")[0]

    # also check parent directory names for context signals
    dirs_lower = set(parts[:-1])

    boost = 0
    if stem in _BOOST_HIGH or dirs_lower & _BOOST_HIGH:
        boost += 5
    elif stem in _BOOST_MED or dirs_lower & _BOOST_MED:
        boost += 2

    if stem in _DEMOTE:
        boost -= 3

    return max(0, base + boost)


def select_files(state: AgentState) -> dict:
    file_tree: list = state.get("file_tree", [])  # [{"path": str, "blob_sha": str}]

    scored = [(item, _score(item["path"])) for item in file_tree]
    scored = [(item, s) for item, s in scored if s > 0]

    # sort: score desc, then shallowest path first, then alphabetical
    scored.sort(key=lambda x: (-x[1], x[0]["path"].count("/"), x[0]["path"]))

    dir_count: dict[str, int] = {}
    selected: list[dict] = []
    for item, _ in scored:
        path      = item["path"]
        directory = path.rsplit("/", 1)[0] if "/" in path else ""
        if dir_count.get(directory, 0) >= DIR_CAP:
            continue
        dir_count[directory] = dir_count.get(directory, 0) + 1
        selected.append(item)
        if len(selected) >= MAX_FILES:
            break

    return {"selected_files": selected}
