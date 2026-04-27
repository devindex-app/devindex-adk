"""Node: call Gemini with structured output to produce a SkillVector."""

import os
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI

from agent.state import AgentState
from models.skill_vector import SkillVector

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "scoring_v1.md"
_MODEL_ID = "gemini-2.5-pro"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _build_file_contents_block(file_contents: dict) -> str:
    parts = []
    for path, content in file_contents.items():
        parts.append(f"### {path}\n```\n{content}\n```")
    return "\n\n".join(parts)


def score_skills(state: AgentState) -> dict:
    username = state["username"]
    repo_full_name = state["repo_full_name"]
    language_bytes: dict = state.get("language_bytes", {})
    file_contents: dict = state.get("file_contents", {})
    complexity_score: float = state.get("complexity_score", 0.0)

    primary_language = (
        max(language_bytes, key=language_bytes.get)
        if language_bytes else "unknown"
    )
    languages_str = ", ".join(
        f"{lang} ({bytes_:,} bytes)"
        for lang, bytes_ in sorted(language_bytes.items(), key=lambda x: -x[1])
    ) or "unknown"

    prompt_template = _load_prompt()
    prompt = prompt_template.format(
        username=username,
        repo_full_name=repo_full_name,
        primary_language=primary_language,
        languages=languages_str,
        complexity_score=f"{complexity_score:.3f}",
        file_contents=_build_file_contents_block(file_contents),
    )

    llm = ChatGoogleGenerativeAI(
        model=_MODEL_ID,
        temperature=0,
        top_p=0.0001,
        google_api_key=os.environ.get("GOOGLE_API_KEY", ""),
    )
    structured_llm = llm.with_structured_output(SkillVector)

    result: SkillVector = structured_llm.invoke(prompt)
    return {"skill_vector": result.model_dump()}
