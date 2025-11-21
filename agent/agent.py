import sys
from collections.abc import AsyncGenerator
import json

if sys.version_info >= (3, 12):
    from typing import override
else:
    def override(func):
        return func

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from tools.github_tools import GithubTools
from models.skill_vector import SkillVector
from utils.structure_output import structure_output
from utils.model import GEMINI_2_5_FLASH, GEMINI_2_5_PRO


class DevIndexAgent(BaseAgent):
    """An agent that analyzes GitHub repository code and generates skill vectors."""

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        username = ctx.session.state.get("username")
        if not username:
            yield Event(content={"role": "user", "parts": [{"text": "Please provide a GitHub username."}]})
            return

        repo = ctx.session.state.get("repo")
        if not repo:
            yield Event(content={"role": "user", "parts": [{"text": "Please provide a repository name (e.g., 'owner/repo' or just 'repo' if owned by user)."}]})
            return

        working_dir = ctx.session.state.get("working_dir", ".")
        github_tools = GithubTools(working_dir=working_dir)

        # Determine full repo name (owner/repo)
        if "/" not in repo:
            repo_full_name = f"{username}/{repo}"
            owner = username
        else:
            repo_full_name = repo
            owner = repo.split("/")[0]

        # Single agent that analyzes repository code and generates skill vector
        analyze_repo_agent = LlmAgent(
            name="analyze_repo_and_generate_skills",
            model=GEMINI_2_5_PRO,
            instruction=f"""
<task>
You are a senior developer. Your task is to analyze the repository '{repo_full_name}' and generate a skill vector based on the current code structure and quality. You will use the tools provided to you to get the information you need.
</task>

<steps>
<step number="1" name="Get repository overview">
- Use fetch_repo_details to get repository metadata (description, topics, etc.)
- Use fetch_repo_languages to get the language breakdown
</step>

<step number="2" name="Get all file paths">
- Use fetch_repo_file_paths to get a list of all files in the repository
- This will give you the structure of the codebase
- Note: The tool automatically filters out irrelevant directories like node_modules, .git, __pycache__, dist, build, vendor, and other build/cache/dependency directories
</step>

<step number="3" name="Analyze key files">
- Review the file paths to identify important files (main entry points, configuration files, core modules, etc.)
- IMPORTANT: Ignore and do not analyze files from:
  * node_modules, vendor, bower_components (dependency directories)
  * .git, .svn, .hg (version control directories)
  * __pycache__, .pytest_cache, .mypy_cache (cache directories)
  * dist, build, out, bin, obj (build output directories)
  * .next, .nuxt, .cache (framework build directories)
  * coverage, .nyc_output (test coverage directories)
  * .idea, .vscode, .settings (IDE configuration directories)
  * venv, .venv, env (virtual environment directories)
- Use fetch_repo_file to read the contents of key files that demonstrate:
  * Architecture and design patterns
  * Code quality and best practices
  * Technologies and frameworks used
  * Error handling and testing
  * Project structure and organization
- Focus on reading a representative sample (10-20 key files) that best showcase the codebase
</step>

<step number="4" name="Generate skill scores based on analysis">
Analyze the repository code and structure to generate skill scores (0-100) for:

- Programming languages (JavaScript, Python, Java, C++, Go, Rust, etc.)
- Frontend frameworks (React, Vue, Angular, Next.js, etc.)
- Backend frameworks (Express, Django, Flask, Spring, etc.)
- Tools and technologies (Docker, Kubernetes, AWS, CI/CD, etc.)
- Specialized domains (Game Development, Unity, Unreal Engine, Mobile Dev, etc.)
</step>
</steps>

<scoring_guidelines>
- 80-100: Expert level - Advanced code patterns, sophisticated architecture, production-ready code quality
- 60-79: Proficient - Well-structured code, good practices, solid understanding demonstrated
- 40-59: Intermediate - Functional code, some good patterns, moderate complexity
- 20-39: Beginner - Basic code structure, simple implementations, learning patterns
- 0-19: Minimal/None - Very limited or no evidence of this skill
</scoring_guidelines>

<scoring_factors>
Consider these factors when scoring:
- Languages and technologies used in the codebase
- Code quality: clean code, error handling, testing, documentation
- Architecture patterns: design patterns, project structure, separation of concerns
- Framework usage: proper use of frameworks, libraries, and tools
- Code complexity and maintainability
- Best practices: following language/framework conventions
- Repository structure and organization
</scoring_factors>

<output_format>
Username: {username}
Repository: {repo_full_name}
Skills identified:
- [skill_name]: [score] - [brief reasoning based on code analysis]
- [skill_name]: [score] - [brief reasoning based on code analysis]
...
</output_format>

<instructions>
Output the skills as a list where each skill has a name and score. Include all relevant skills found. Don't include skills with no evidence (score 0).

Focus on analyzing the actual code quality and structure, not just what technologies are mentioned.
</instructions>
            """,
            tools=[
                github_tools.fetch_repo_details,
                github_tools.fetch_repo_languages,
                github_tools.fetch_repo_file_paths,
                github_tools.fetch_repo_file,
            ],
            output_key="raw_skill_vector",
        )
        ctx.branch = analyze_repo_agent.name
        async for event in analyze_repo_agent.run_async(ctx):
            yield event

        if "raw_skill_vector" not in ctx.session.state:
            yield Event(content={"role": "user", "parts": [{"text": "Failed to generate skill vector."}]})
            return

        # Structure the skill vector output
        async for event in structure_output(
            input_key="raw_skill_vector",
            schema=SkillVector,
            output_key="skill_vector",
            ctx=ctx,
            model=GEMINI_2_5_FLASH
        ):
            yield event

        if "skill_vector" not in ctx.session.state:
            yield Event(content={"role": "user", "parts": [{"text": "Failed to structure skill vector."}]})
            return

        # Format and store the final skill vector
        skill_vector_data = ctx.session.state.get("skill_vector", {})
        skills_list = skill_vector_data.get("skills", [])
        
        # Convert to dict for easier access and display
        skills_dict = {skill["name"]: skill["score"] for skill in skills_list if isinstance(skill, dict)}
        
        # Format the output nicely
        formatted_skills = [f"  {name}: {score}" for name, score in sorted(skills_dict.items(), key=lambda x: x[1], reverse=True)]
        output = f"""
Skill Vector for {skill_vector_data.get('username', username)} (Repository: {repo_full_name}):
{chr(10).join(formatted_skills) if formatted_skills else '  No skills identified'}
        """.strip()

        # Store the formatted output in session state
        ctx.session.state["skill_vector_output"] = output
        ctx.session.state["skill_vector_dict"] = skills_dict