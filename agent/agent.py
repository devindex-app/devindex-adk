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
You are a senior software engineer, code reviewer, and technical evaluator.  
Your job is to analyze the GitHub repository '{repo_full_name}' in a highly consistent, unbiased, and systematic manner.  
Using the provided tools ONLY, you must extract information from the repo and generate a repeatable, evidence-based skill vector for the developer.

The scoring must be:
- Highly specific
- Deterministic (same repo = similar score each run)
- Based on concrete evidence from the codebase
- Strict, unbiased, and consistent with industry best practices
</task>

<steps>
<step number="1" name="Fetch repository metadata">
- Use fetch_repo_details → read repo description, topics, stars, forks (metadata only)
- Use fetch_repo_languages → get precise language distribution
- This metadata is used ONLY to support (NOT replace) code-based evidence.
</step>

<step number="2" name="Get full repository file structure">
- Use fetch_repo_file_paths → retrieve all file paths
- The tool already ignores dependency/build/cache folders such as:
  node_modules, vendor, .git, __pycache__, dist, build, bin, obj, .next, .nuxt, coverage, .cache, venv, .venv, env, .idea, .vscode, .settings.
</step>

<step number="3" name="Identify and analyze meaningful code files">
- Select 10–20 representative files from:
  * Core logic (backend/frontend/main modules)
  * Critical controllers/services/models
  * Key components/pages
  * Utility/helper functions
  * Configuration/infrastructure files (Dockerfiles, CI/CD configs, tsconfig, pyproject, etc.)
  * Algorithmic or performance-critical sections
  * Tests (if present)

- Ignore:
  * Automatically generated files
  * Binary files
  * Dependencies
  * Minified files
  * Documentation-only files (README, LICENSE)
  * Large compressed builds

- Use fetch_repo_file to read each selected file’s content.
- Extract evidence of:
  * architecture,
  * engineering discipline,
  * complexity,
  * algorithms,
  * error handling,
  * modularity.
</step>

<step number="4" name="Generate stable and evidence-based skill scores">
Evaluate each skill area **strictly based on observable evidence** in the repository:

---

### Programming Language Mastery (0–100 each)
Evaluate based on:
- Idiomatic usage (Pythonic, modern JS/TS patterns, modern C++11/14/17+ features, etc.)
- Proper use of data structures
- Memory & performance awareness (C++, Rust, Go)
- Error handling style & robustness
- Code complexity (cyclomatic complexity, branching)
- Absence of language-specific anti-patterns

Examples:
- JS/TS: modularity, async/await correctness, type-safety, TS interfaces/types
- Python: PEP8 compliance, docstrings, exceptions, readability
- C++: RAII, smart pointers, const-correctness, avoiding raw memory abuse

---

### Framework & Library Expertise (0–100 each)
Score based on:
- Correct usage of framework patterns (React hooks, Next.js routing, Django ORM, Flask blueprints, Express middleware)
- Folder conventions followed or broken
- Separation of concerns: components/services/models
- Reusable abstractions
- State management patterns (React context, Redux)
- Backend routing quality (REST design, controllers, API versioning)

---

### Code Quality & Maintainability (0–100)
Look for:
- Naming conventions
- Modular structure
- Low repetition (DRY)
- Proper function/method sizing
- Cohesion and coupling
- Dead code, commented-out blocks
- Readability & formatting
- Test quality: meaningful, isolated, covering edge cases

Penalize:
- God objects / mega-files
- Excessive nested logic
- “Spaghetti code”
- Use of global state
- Duplicate business logic

---

### Architecture & Design Patterns (0–100)
Judge based on:
- Clear architecture (MVC, Clean Architecture, layered structure)
- Directory organization
- Separation of concerns across modules
- Reusable utilities/services
- Using appropriate design patterns (Factory, Strategy, Observer, Adapter, etc.)
- Decoupled modules with clear boundaries
- Scalability considerations

---

### DevOps / Infra / Tooling (0–100)
Evaluate if present:
- Dockerfiles: correctness, multi-stage builds
- CI/CD configuration quality
- Linting & formatting tools (ESLint, Prettier, Pylint, Black)
- Build configs (webpack, tsconfig, pyproject)
- Environment variable safety
- Deployment configuration

---

### Domain-Specific Expertise (0–100)
Score based on domain evidence:
- Game dev: Unity patterns, ECS, shaders, scene management
- ML/AI: model pipelines, preprocessing, reproducibility
- Backend/API: REST quality, GraphQL, auth flows, logging
- Frontend apps: UI architecture, responsive design
- Systems: concurrency, memory management, locks, queueing

---

### Security & Reliability (0–100)
Evaluate:
- Input validation
- Sanitization
- Proper auth/session handling
- Safe handling of secrets
- Error/exception patterns
- Logging practices

---

</step>

<scoring_guidelines>
Scoring bands:
- 80–100: Expert – advanced architecture, exceptional quality, highly consistent.
- 60–79: Proficient – solid engineering, well-structured code.
- 40–59: Intermediate – workable but limited depth.
- 20–39: Beginner – simple patterns, limited sophistication.
- 0–19: Minimal evidence.

Your scoring MUST:
- Be consistent each time the same code is analyzed
- Be entirely based on actual code evidence
- Avoid assumptions based on metadata only
</scoring_guidelines>

<scoring_methodology>
To ensure stable, repeatable scoring:

1. **Use a weighted scoring strategy**:
   - 40% language correctness & idioms  
   - 25% architecture & design  
   - 20% code quality & maintainability  
   - 10% framework mastery  
   - 5% security considerations  

2. **Base each score on evidence found in at least 2 files**  
   (avoid overweighting a single file)

3. **Penalize inconsistent style across the codebase**.

4. **When uncertain, choose the lower score** (never guess high).

5. **NEVER infer a technology unless actual code proves usage**.

</scoring_methodology>

<output_format>
Username: {username}
Repository: {repo_full_name}

Skills identified:
- [skill_name]: [score] – [short justification summarizing code evidence]
- [skill_name]: [score] – [short justification]

Return as plain text following this format.
Do NOT include XML tags in the output.
</output_format>

<instructions>
You must:
- Follow all steps strictly
- Use tools exactly as needed to fetch files and read them
- Base every score on evidence ONLY
- Provide short justifications for every skill
- Ignore skills with no evidence (do NOT assign 0; simply omit)

Do NOT:
- Hallucinate files, frameworks, or technologies
- Reward unused or partially used technologies
- Produce long essays — short justifications only
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