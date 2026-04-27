"""Node: clamp all skill scores to [0, 100] and build validated_skills dict."""

from agent.state import AgentState


def validate_scores(state: AgentState) -> dict:
    raw: dict = state.get("skill_vector") or {}
    skills_list: list = raw.get("skills", [])

    validated: dict[str, int] = {}
    for item in skills_list:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip().lower()
        score = item.get("score", 0)
        if not name:
            continue
        try:
            score = max(0, min(100, int(score)))
        except (TypeError, ValueError):
            score = 0
        validated[name] = score

    if not validated:
        return {"error": "LLM returned no skills", "error_class": "ScoringError"}

    return {"validated_skills": validated}
