"""Node: deterministically select ≤20 representative files.

Algorithm (reproducible given the same file list):
1. Score every file by extension/name priority.
2. Sort scored files by (priority desc, depth asc, path asc).
3. Take the top MAX_FILES, but cap any single directory at DIR_CAP files
   to avoid over-weighting monolithic folders.
"""

from agent.state import AgentState

MAX_FILES = 20
DIR_CAP = 5   # max files from any single directory

# Higher priority → more likely to be selected
_PRIORITY: dict[str, int] = {
    # core logic
    ".py": 10, ".ts": 10, ".tsx": 10, ".go": 10, ".rs": 10,
    ".java": 10, ".kt": 10, ".cpp": 10, ".cc": 10, ".cxx": 10,
    ".c": 9, ".cs": 9, ".rb": 9, ".swift": 9,
    # web
    ".js": 8, ".jsx": 8, ".vue": 8, ".svelte": 8,
    # config / infra
    "dockerfile": 7, ".yaml": 6, ".yml": 6, ".toml": 6,
    ".json": 5, ".tf": 7, ".bicep": 7,
    # tests get moderate priority
    "_test": 6, ".test.": 6, "spec.": 6,
    # docs / markup — lowest
    ".md": 1, ".txt": 1, ".rst": 1, ".html": 3, ".css": 3, ".scss": 3,
}

_SKIP_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock"}
_SKIP_SUFFIXES = (".min.js", ".min.css", ".bundle.js", ".map", ".lock", ".sum")

# Second-layer dir filter (list_files already does this, but belt-and-suspenders)
_IGNORED_DIRS = {
    "node_modules", "dist", "build", ".git", "__pycache__", "vendor",
    "venv", ".venv", "coverage", ".next", ".nuxt", "target", "out",
}


def _score(path: str) -> int:
    lower = path.lower()
    parts = lower.split("/")
    name = parts[-1]

    # ignore if any path component is a known build/dep dir
    if any(p in _IGNORED_DIRS for p in parts[:-1]):
        return -1
    if name in _SKIP_NAMES:
        return -1
    if any(lower.endswith(s) for s in _SKIP_SUFFIXES):
        return -1
    # generated
    if "generated" in lower or ".g." in lower or "autogen" in lower:
        return -1

    for key, pri in _PRIORITY.items():
        if lower.endswith(key) or key in lower:
            return pri
    return 4  # unknown extension → below JS, above docs


def select_files(state: AgentState) -> dict:
    all_paths: list = state.get("file_paths", [])

    # score + filter
    scored = [(p, _score(p)) for p in all_paths]
    scored = [(p, s) for p, s in scored if s >= 0]

    # sort: priority desc, depth asc, path asc (depth = number of "/" chars)
    scored.sort(key=lambda x: (-x[1], x[0].count("/"), x[0]))

    # directory cap to avoid over-sampling monolithic folders
    dir_count: dict[str, int] = {}
    selected: list[str] = []
    for path, _ in scored:
        directory = path.rsplit("/", 1)[0] if "/" in path else ""
        if dir_count.get(directory, 0) >= DIR_CAP:
            continue
        dir_count[directory] = dir_count.get(directory, 0) + 1
        selected.append(path)
        if len(selected) >= MAX_FILES:
            break

    return {"selected_files": selected}
