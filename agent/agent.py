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
    """An agent that analyzes GitHub user profiles and generates skill vectors."""

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
        else:
            repo_full_name = repo
            # Extract owner from repo if provided
            owner = repo.split("/")[0]

        # Step 1: Fetch repository details
        analyze_repo_agent = LlmAgent(
            name="analyze_repo",
            model=GEMINI_2_5_FLASH,
            instruction=f"""
Use the fetch_repo_details tool to get detailed information about repository '{repo_full_name}'.
Then use fetch_repo_languages to get the language breakdown for this repository.
Summarize:
- Repository description and purpose
- Primary programming languages used
- Repository topics/tags
- Size and activity indicators
- Repository metadata
            """,
            tools=[github_tools.fetch_repo_details, github_tools.fetch_repo_languages],
            output_key="repo_analysis",
        )
        ctx.branch = analyze_repo_agent.name
        async for event in analyze_repo_agent.run_async(ctx):
            yield event

        if "repo_analysis" not in ctx.session.state:
            yield Event(content={"role": "user", "parts": [{"text": "Failed to fetch repository information."}]})
            return

        # Step 2: Fetch and analyze pull requests for this specific repository
        analyze_prs_agent = LlmAgent(
            name="analyze_prs",
            model=GEMINI_2_5_FLASH,
            instruction=f"""
Use the fetch_user_pull_requests tool to get pull requests created by user '{username}'.
Focus on PRs that are related to repository '{repo_full_name}'.
Analyze the PRs to identify:
- Technologies, frameworks, and tools mentioned in PR descriptions
- Code quality indicators (descriptive PR titles, detailed descriptions)
- Technologies worked on in PRs related to this repository
            """,
            tools=[github_tools.fetch_user_pull_requests],
            output_key="prs_analysis",
        )
        ctx.branch = analyze_prs_agent.name
        async for event in analyze_prs_agent.run_async(ctx):
            yield event

        # Step 3: Fetch commits and their actual code changes (diffs)
        analyze_commits_agent = LlmAgent(
            name="analyze_commits",
            model=GEMINI_2_5_FLASH,
            instruction=f"""
First, use fetch_user_commits tool with per_page=5 to get the 5 most recent commits 
for repository '{repo_full_name}' by user '{username}'.

Then, for each commit SHA returned, use fetch_commit_diff to get the actual code changes (diffs) 
for that commit. Extract the owner and repo from '{repo_full_name}' (format: owner/repo).

Analyze:
- The actual code changes (patches/diffs) in each commit
- Code quality: proper error handling, clean code, good practices
- Technologies and frameworks used in the code changes
- Commit message quality and whether it matches the changes
- Code complexity and maintainability indicators
- Whether the changes show good software engineering practices

Focus on analyzing the actual code diff/patches, not just commit messages.
            """,
            tools=[github_tools.fetch_user_commits, github_tools.fetch_commit_diff],
            output_key="commits_analysis",
        )
        ctx.branch = analyze_commits_agent.name
        async for event in analyze_commits_agent.run_async(ctx):
            yield event

        # Step 4: Generate skill vector based on collected data from the specific repository
        generate_skills_agent = LlmAgent(
            name="generate_skills",
            model=GEMINI_2_5_PRO,
            instruction=f"""
Analyze the collected GitHub data for user '{username}' from repository '{repo_full_name}' and generate a skill vector.

Consider the following data sources:
1. Repository languages and technologies (from repo_analysis)
2. Technologies and frameworks from PR descriptions (from prs_analysis) - focus on PRs for this repo
3. Actual code changes (diffs/patches) from commits_analysis - analyze the code quality, technologies, and patterns in the actual code changes, not just commit messages
4. Repository topics, descriptions, and purpose
5. Code quality indicators from actual code changes: error handling, clean code practices, testing, architecture patterns

Generate skill scores (0-100) for:
- Programming languages (JavaScript, Python, Java, C++, Go, Rust, etc.)
- Frontend frameworks (React, Vue, Angular, Next.js, etc.)
- Backend frameworks (Express, Django, Flask, Spring, etc.)
- Tools and technologies (Docker, Kubernetes, AWS, CI/CD, etc.)
- Specialized domains (Game Development, Unity, Unreal Engine, Mobile Dev, etc.)

Scoring guidelines:
- 80-100: Expert level - Significant contributions, advanced usage, leadership in this area
- 60-79: Proficient - Strong experience, multiple projects, good understanding
- 40-59: Intermediate - Moderate experience, some projects, working knowledge
- 20-39: Beginner - Limited experience, basic usage, learning phase
- 0-19: Minimal/None - Very limited or no evidence of this skill

Consider these factors:
- Languages used in the repository
- Technologies and frameworks found in actual code changes (diffs)
- Code quality from analyzing actual patches: clean code, error handling, testing, design patterns
- Technologies from PR descriptions
- Repository complexity and purpose
- Code quality indicators from both code diffs and commit messages

Output format:
Username: {username}
Repository: {repo_full_name}
Skills identified:
- [skill_name]: [score] - [brief reasoning]
- [skill_name]: [score] - [brief reasoning]
...

Output the skills as a list where each skill has a name and score. Include all relevant skills found. Don't include skills with no evidence (score 0).

Here is the collected commit analysis data to perform skill evaluation from:
{ctx.session.state['commits_analysis']}
            """,
            output_key="raw_skill_vector",
        )
        ctx.branch = generate_skills_agent.name
        async for event in generate_skills_agent.run_async(ctx):
            yield event

        if "raw_skill_vector" not in ctx.session.state:
            yield Event(content={"role": "user", "parts": [{"text": "Failed to generate skill vector."}]})
            return

        # Step 5: Structure the skill vector output
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

        # Step 6: Format and display the final skill vector
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

        # Store the formatted output in session state instead of yielding Event
        # This avoids the Event author field requirement issue
        ctx.session.state["skill_vector_output"] = output
        ctx.session.state["skill_vector_dict"] = skills_dict
        
        # Output via session state - the main.py will handle displaying it
        # The skill vector data is available in ctx.session.state["skill_vector_dict"]