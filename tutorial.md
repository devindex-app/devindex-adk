# Multi-Agent Workflows with Google ADK Python

## 🚨 Critical Implementation Notes (Lessons Learned)

### Common Pitfalls and Solutions

**0. Async Generator Control Flow (CRITICAL)**

**Issue A: Missing return after yielding error events**
```python
# ❌ WRONG - Missing return after yielding error events
async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
    if "required_data" not in ctx.session.state:
        yield Event(content={"role": "user", "parts": [{"text": "Error: Missing data"}]})
        # Missing return here causes async generator state corruption

    # More code continues executing, causing "object async_generator can't be used in 'await' expression"
    next_step = LlmAgent(...)
    async for event in next_step.run_async(ctx):
        yield event

# ✅ CORRECT - Always return after yielding error events
async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
    if "required_data" not in ctx.session.state:
        yield Event(content={"role": "user", "parts": [{"text": "Error: Missing data"}]})
        return  # Critical: Prevents async generator state corruption

    # Continue with normal flow only if validation passes
    next_step = LlmAgent(...)
    async for event in next_step.run_async(ctx):
        yield event
```

**Issue B: Incorrect helper method signatures and usage (CRITICAL)**
```python
# ❌ WRONG - Helper methods that yield events but have incorrect signatures
class MyAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # This causes "object async_generator can't be used in 'await' expression"
        await self._fetch_data(ctx)  # WRONG - Cannot await async generator
        await self._process_data(ctx)  # WRONG - Cannot await async generator

    # Wrong signature - should be AsyncGenerator[Event, None] if yielding events
    async def _fetch_data(self, ctx: InvocationContext) -> None:
        agent = LlmAgent(...)
        async for event in agent.run_async(ctx):
            yield event  # This makes it an async generator, not a regular async function

# ✅ CORRECT - Helper methods with proper signatures and usage
class MyAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # Yield from helper methods instead of awaiting them
        async for event in self._fetch_data(ctx):
            yield event

        async for event in self._process_data(ctx):
            yield event

    # Correct signature - AsyncGenerator[Event, None] for methods that yield events
    async def _fetch_data(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        agent = LlmAgent(...)
        async for event in agent.run_async(ctx):
            yield event

    async def _process_data(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        agent = LlmAgent(...)
        async for event in agent.run_async(ctx):
            yield event
```

**Key Rules:**
1. **If a helper method yields events** → Use `AsyncGenerator[Event, None]` return type and `async for event in helper_method(): yield event`
2. **If a helper method doesn't yield events** → Use regular async function signature and `await helper_method()`
3. **Never `await` an async generator** → This causes the "object async_generator can't be used in 'await' expression" error

**4. Python Version Compatibility (CRITICAL)**

**Issue: ImportError with `typing.override` on Python < 3.12**
```python
# ❌ WRONG - This fails on Python 3.11 and earlier
from typing import override

class MyAgent(BaseAgent):
    @override  # ImportError: cannot import name 'override' from 'typing'
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        pass

# ✅ CORRECT - Version-compatible override decorator
from collections.abc import AsyncGenerator
import sys

# Handle Python version compatibility for override decorator
if sys.version_info >= (3, 12):
    from typing import override
else:
    # For Python < 3.12, create a no-op override decorator
    def override(func):
        return func

class MyAgent(BaseAgent):
    @override  # Works on all Python versions
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        pass
```

**Why this happens:**
- `typing.override` was introduced in Python 3.12
- Many users are still on Python 3.11 or earlier
- The template must be compatible with all Python versions

**Solution:**
- Always use the version-compatible import pattern shown above
- The no-op decorator provides the same functionality for older Python versions
- This ensures your agents work across all Python environments

**1. Agent Tool Response Handling**
```python
# ✅ CORRECT - Proper tool response handling
from google.adk.agents import Agent

agent = Agent(
    name="weather_agent",
    model="gemini-2.0-flash",
    tools=[get_weather_tool],
)

# Tools should return structured responses
def get_weather_tool(city: str) -> dict:
    try:
        weather_data = fetch_weather(city)
        return {
            "status": "success",
            "report": f"Weather in {city}: {weather_data}",
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to get weather: {str(e)}",
        }
```

**2. Structured Output and JSON Validation (CRITICAL)**
```python
# ❌ WRONG - Using output_schema directly on LlmAgent
# This causes JSON validation errors when LLM doesn't produce perfect JSON
task_agent = LlmAgent(
    name="task_agent",
    model=GEMINI_2_5_FLASH,
    instruction="Generate structured data...",
    output_schema=MyPydanticModel,  # AVOID THIS - causes JSON validation errors
    output_key="structured_result",
)

# ✅ CORRECT - Two-step approach with XML tags and separate structure_output function
from pydantic import BaseModel
from typing import List
from utils.structure_output import structure_output

class MyItem(BaseModel):
    """Individual item model - must inherit from BaseModel"""
    id: str
    name: str
    status: str

class MyResult(BaseModel):
    """Wrapper model for lists - ALWAYS wrap lists in BaseModel"""
    success: bool
    message: str
    items: List[MyItem]  # Lists must be wrapped inside BaseModel
    total_count: int

# Usage in your agent with XML schema tags:
class MyWorkflowAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # Step 1: Generate raw output with XML schema tags in instruction
        task_agent = LlmAgent(
            name="task_agent",
            model=GEMINI_2_5_FLASH,
            instruction=f"""
Your task description here...

Analyze the data and create a structured response.

Output the result in the following JSON schema:
<output_json_schema>
{MyResult.model_json_schema()}
</output_json_schema>

Make sure to:
1. Set success to true/false based on completion
2. Provide a descriptive message
3. Create items list with relevant data
4. Set total_count to the number of items
            """,
            output_key="raw_result",  # Raw output first, no output_schema here
        )

        async for event in task_agent.run_async(ctx):
            yield event

        # Step 2: Structure the raw output using proper BaseModel wrapper
        async for event in structure_output(input_key="raw_result", schema=MyResult, output_key="structured_result", ctx=ctx):
            yield event

        # Step 3: Use structured result
        if "structured_result" in ctx.session.state:
            structured_data = ctx.session.state.get("structured_result","")
            # CRITICAL: structured_data is a DICT, not a Pydantic model instance
            # You MUST access fields using dictionary notation: structured_data['field_name']
            success = structured_data['success']
            items = structured_data['items']
            message = structured_data['message']
```

**CRITICAL BaseModel Requirements:**
- **NEVER** use `List[Model]`, `Dict[str, Model]`, or any generic types directly in `output_schema`
- **ALWAYS** wrap lists and complex types in a BaseModel class
- **USE** `<output_json_schema>{Model.model_json_schema()}</output_json_schema>` XML tags in instructions **ONLY when you need structured output**
- **ONLY** use `output_schema` parameter in the `structure_output` function, never on main LLM agents

**CRITICAL: Session State Data Access**
The `structure_output` utility stores data as **DICTIONARY** in `ctx.session.state`, not as Pydantic model instances. Use bracket notation: `data['field']` not `data.field`.

**3. Required Imports for ADK Development**
```python
# Always include these imports for agent work
from collections.abc import AsyncGenerator
import sys

# Handle Python version compatibility for override decorator
if sys.version_info >= (3, 12):
    from typing import override
else:
    # For Python < 3.12, create a no-op override decorator
    def override(func):
        return func

from google.adk.agents import Agent, LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.core import Runner
from google.adk.sessions.in_memory import InMemorySessionService
from pydantic import BaseModel
from utils.model import GEMINI_2_5_FLASH
```

## Agent Naming Conventions

### Agent Name Requirements
Agent names must be valid Python identifiers and follow these rules:
- Must start with a letter (a-z, A-Z) or underscore (_)
- Can only contain letters, digits (0-9), and underscores
- Cannot contain hyphens (-), spaces, or special characters
- Cannot be Python reserved words (like `class`, `def`, `if`, etc.)

**Examples:**
```python
# ✅ VALID agent names
agent = LlmAgent(name="code_reviewer")
agent = LlmAgent(name="data_processor")
agent = LlmAgent(name="_private_agent")
agent = LlmAgent(name="ReviewAgent2")

# ❌ INVALID agent names - will cause validation errors
agent = LlmAgent(name="review-agent")  # Contains hyphen
agent = LlmAgent(name="review agent")  # Contains space
agent = LlmAgent(name="2nd_reviewer")  # Starts with digit
agent = LlmAgent(name="class")  # Python reserved word
```


## Building Advanced Agents with ADK (Recommended Pattern)

This guide shows how to build robust, multi-step workflow agents in ADK using a custom agent class. This pattern is recommended for any advanced, stateful, or multi-stage automation.

**Best Practice:**
- For each sub-agent (LlmAgent), only pass the tools that are actually needed for that step. Do not declare or pass extra tools that are not required.
- Implement your agent in an iterative, step-by-step fashion: the main agent should run each LllmAgent in sequence, yielding events and checking for required state after each step.
- **CRITICAL**: Always set `ctx.branch = agent.name` before calling `agent.run_async(ctx)` to maintain separate conversation contexts for each sub-agent.

### Step-by-Step: Creating a Multi-Step Workflow Agent

1. **Inherit from BaseAgent and Structure Your Workflow**
   - Subclass `BaseAgent`
   - Override `async def _run_async_impl(self, ctx)`
   - Use `ctx.session.state` to read and write data between steps
   - Chain sub-agents with `output_key` to store results in session state
   - Check for required state and handle errors between steps
   - Yield `Event` objects to stream progress/results
   - Place all agent logic in `agent.py`, minimal entrypoint in `main.py`

2. **Example: Multi-Step Workflow Agent**

```python
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.events import Event
from google.adk.agents.invocation_context import InvocationContext
from typing import AsyncGenerator
from tools.SampleTools import CodeEditingTools

class MyWorkflowAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        working_dir = ctx.session.state.get("working_dir", ".")
        
        # Step 1: First sub-agent (e.g., analyze input)
        analyze = LlmAgent(
            name="analyze",
            instruction="Analyze the input files and summarize findings.",
            tools=[*CodeEditingTools(working_dir=working_dir).get_tools()],
            output_key="analysis_result",
        )
        ctx.branch = analyze.name
        async for event in analyze.run_async(ctx):
            yield event

        # Check for required state after each step
        if "analysis_result" not in ctx.session.state:
            yield Event(content={"role": "user", "parts": [{"text": "Analysis failed"}]})
            return

        # Step 2: Second sub-agent (e.g., generate solution)
        solve = LlmAgent(
            name="solve",
            instruction="Given the analysis, generate and implement a solution.",
            tools=[*CodeEditingTools(working_dir=working_dir).get_tools()],
            output_key="solution_result",
        )
        ctx.branch = solve.name
        async for event in solve.run_async(ctx):
            yield event

        # Check for required state
        if "solution_result" not in ctx.session.state:
            yield Event(content={"role": "user", "parts": [{"text": "Solution generation failed"}]})
            return

        # Step 3: Finalize (optional)
        yield Event(content={"role": "user", "parts": [{"text": ctx.session.state["solution_result"]}]})
```

3. **Minimal Entrypoint to Run the Agent**

**For agents that work with git repositories (recommended pattern):**

```python
import argparse
import asyncio
import os

from my_agent import MyWorkflowAgent
import subprocess
from pathlib import Path
from typing import List, Optional

from google.adk.runners import InMemoryRunner
from google.genai import types

app_name = "my_workflow_app"

async def main():

    
    # Validate required environment variables
    raise_if_env_absent(["GOOGLE_API_KEY"])  # Add other keys as needed

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="My Workflow Agent")
    parser.add_argument("--git_url", type=str, required=True, help="Git repository URL to analyze")
    parser.add_argument("--git_branch", type=str, help="Git branch to analyze, else clones default branch")
    args = parser.parse_args()

    

    # Prepare session state
    session_state = {
        "git_url": args.git_url,
        "git_branch": args.git_branch,
        "working_dir": working_dir
    }

    
     runner = InMemoryRunner(
        app_name=app_name,
        agent=MyWorkflowAgent(name="my_workflow_agent"),
    )

    session = await runner.session_service.create_session(app_name=app_name, user_id=user_id, state=session_state)

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text="Follow the system instruction.")]),
    ):
        logger.info(event.model_dump_json(exclude_unset=True, exclude_defaults=True, exclude_none=True))
def run():
    asyncio.run(main())

if __name__ == "__main__":
    run()
```
