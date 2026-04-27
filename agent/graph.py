"""DevIndex LangGraph — builds and returns the compiled graph."""

from langgraph.graph import END, StateGraph

from agent.state import AgentState
from agent.nodes import (
    check_cache,
    compute_complexity,
    compute_hash,
    fetch_files,
    fetch_metadata,
    list_files,
    persist,
    score_skills,
    select_files,
    validate_input,
    validate_scores,
)


def _route_after_cache(state: AgentState) -> str:
    if state.get("error"):
        return "error_end"
    if state.get("cache_hit"):
        return "persist"
    return "list_files"


def _route_after_validate(state: AgentState) -> str:
    return "error_end" if state.get("error") else "fetch_metadata"


def _route_after_validate_scores(state: AgentState) -> str:
    return "error_end" if state.get("error") else "persist"


def _error_node(state: AgentState) -> dict:
    """Terminal node — just surfaces the error (already in state)."""
    return {}


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    # nodes
    g.add_node("validate_input", validate_input)
    g.add_node("fetch_metadata", fetch_metadata)
    g.add_node("compute_hash", compute_hash)
    g.add_node("check_cache", check_cache)
    g.add_node("list_files", list_files)
    g.add_node("select_files", select_files)
    g.add_node("fetch_files", fetch_files)
    g.add_node("compute_complexity", compute_complexity)
    g.add_node("score_skills", score_skills)
    g.add_node("validate_scores", validate_scores)
    g.add_node("persist", persist)
    g.add_node("error_end", _error_node)

    # edges
    g.set_entry_point("validate_input")

    g.add_conditional_edges(
        "validate_input",
        _route_after_validate,
        {"fetch_metadata": "fetch_metadata", "error_end": "error_end"},
    )

    g.add_edge("fetch_metadata", "compute_hash")
    g.add_edge("compute_hash", "check_cache")

    g.add_conditional_edges(
        "check_cache",
        _route_after_cache,
        {
            "list_files": "list_files",
            "persist": "persist",
            "error_end": "error_end",
        },
    )

    g.add_edge("list_files", "select_files")
    g.add_edge("select_files", "fetch_files")
    g.add_edge("fetch_files", "compute_complexity")
    g.add_edge("compute_complexity", "score_skills")
    g.add_edge("score_skills", "validate_scores")

    g.add_conditional_edges(
        "validate_scores",
        _route_after_validate_scores,
        {"persist": "persist", "error_end": "error_end"},
    )

    g.add_edge("persist", END)
    g.add_edge("error_end", END)

    return g.compile()
