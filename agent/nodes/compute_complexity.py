"""Node: heuristic project complexity score (0–1).

Factors:
  - Number of distinct languages (diversity)
  - Total bytes of code
  - Presence of infra files (Dockerfile, CI, Terraform)
  - Presence of tests
  - Directory depth of selected files
"""

import math

from agent.state import AgentState

_INFRA_MARKERS = {
    "dockerfile", ".github/workflows", ".gitlab-ci", "terraform",
    "kubernetes", "k8s", "helm", "docker-compose", "jenkinsfile",
}
_TEST_MARKERS = {"test", "spec", "__tests__", "tests/"}


def compute_complexity(state: AgentState) -> dict:
    language_bytes: dict = state.get("language_bytes", {})
    selected: list = state.get("selected_files", [])
    file_contents: dict = state.get("file_contents", {})

    # 1. language diversity (0–1, log-scaled, saturates at ~8 languages)
    num_langs = max(1, len(language_bytes))
    lang_score = min(1.0, math.log(num_langs + 1) / math.log(9))

    # 2. total code size (0–1, log-scaled, saturates at ~1 MB)
    total_bytes = sum(language_bytes.values()) if language_bytes else 0
    size_score = min(1.0, math.log(total_bytes + 1) / math.log(1_000_001))

    # 3. infra presence
    all_paths_lower = " ".join(p.lower() for p in selected)
    infra_score = 1.0 if any(m in all_paths_lower for m in _INFRA_MARKERS) else 0.0

    # 4. test presence
    test_score = 1.0 if any(m in all_paths_lower for m in _TEST_MARKERS) else 0.0

    # 5. average directory depth of selected files (normalised)
    depths = [p.count("/") for p in selected] if selected else [0]
    avg_depth = sum(depths) / len(depths)
    depth_score = min(1.0, avg_depth / 5.0)

    # weighted composite
    complexity = (
        0.30 * lang_score
        + 0.25 * size_score
        + 0.20 * infra_score
        + 0.15 * test_score
        + 0.10 * depth_score
    )

    details = {
        "num_languages": num_langs,
        "total_bytes": total_bytes,
        "has_infra": infra_score > 0,
        "has_tests": test_score > 0,
        "avg_depth": round(avg_depth, 2),
        "components": {
            "lang_score": round(lang_score, 3),
            "size_score": round(size_score, 3),
            "infra_score": infra_score,
            "test_score": test_score,
            "depth_score": round(depth_score, 3),
        },
    }

    return {
        "complexity_score": round(complexity, 4),
        "complexity_details": details,
    }
