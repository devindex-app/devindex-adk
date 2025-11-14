from typing import AsyncGenerator
from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from pydantic import BaseModel
from utils.model import GEMINI_2_5_FLASH


def structure_output(
    input_key: str, 
    schema: BaseModel, 
    output_key: str, 
    ctx: InvocationContext, 
    model: str = None
) -> AsyncGenerator[Event, None]:
    """
    Structure raw output using a separate LLM call with schema validation.
    This prevents JSON validation errors by using a two-step process:
    1. First LLM generates raw output
    2. Second LLM structures it according to the schema
    
    Args:
        input_key: Key in ctx.session.state containing the raw output to structure
        schema: Pydantic BaseModel schema to validate against
        output_key: Key to store the structured output in ctx.session.state
        ctx: InvocationContext
        model: Model name (defaults to GEMINI_2_5_FLASH)
    """
    if model is None:
        model = GEMINI_2_5_FLASH
    
    name = f"structure_output_{input_key}_{output_key}"
    
    # Get the raw output from session state
    raw_output = ctx.session.state.get(input_key, "")
    
    get_structured_output = LlmAgent(
        name=name,
        model=model,
        instruction=f"""
Extract and structure the following output according to the JSON schema.
The output should contain a username and a list of skills, where each skill has a name and score.

Raw output to structure:
{raw_output}

Output the result in the following JSON schema:
<output_json_schema>
{schema.model_json_schema()}
</output_json_schema>

Parse the raw output and create a properly structured response matching the schema exactly.
The skills should be in a list format where each item has "name" and "score" fields.
        """,
        output_key=output_key,
        output_schema=schema,
    )

    ctx.branch = name
    return get_structured_output.run_async(ctx) 