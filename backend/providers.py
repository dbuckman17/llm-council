"""Direct provider API clients for OpenAI, Anthropic, and Google."""

import asyncio
from typing import List, Dict, Any, Optional

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from google import genai

from .config import OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, USE_VERTEX_AI, GCP_PROJECT, GCP_LOCATION

# Instantiate SDK clients at module level for connection reuse
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Google client: Vertex AI (service account auth) or API key
if USE_VERTEX_AI and GCP_PROJECT:
    google_client = genai.Client(vertexai=True, project=GCP_PROJECT, location=GCP_LOCATION)
elif GOOGLE_API_KEY:
    google_client = genai.Client(api_key=GOOGLE_API_KEY)
else:
    google_client = None

MAX_TOOL_ROUNDS = 5


def _extract_openai_usage(response) -> dict:
    """Extract token usage from an OpenAI response."""
    if not hasattr(response, "usage") or response.usage is None:
        return {"input_tokens": 0, "output_tokens": 0}
    return {
        "input_tokens": response.usage.prompt_tokens or 0,
        "output_tokens": response.usage.completion_tokens or 0,
    }


def _extract_anthropic_usage(response) -> dict:
    """Extract token usage from an Anthropic response."""
    if not hasattr(response, "usage") or response.usage is None:
        return {"input_tokens": 0, "output_tokens": 0}
    return {
        "input_tokens": response.usage.input_tokens or 0,
        "output_tokens": response.usage.output_tokens or 0,
    }


def _extract_google_usage(response) -> dict:
    """Extract token usage from a Google response."""
    if not hasattr(response, "usage_metadata") or response.usage_metadata is None:
        return {"input_tokens": 0, "output_tokens": 0}
    return {
        "input_tokens": response.usage_metadata.prompt_token_count or 0,
        "output_tokens": response.usage_metadata.candidates_token_count or 0,
    }


def get_provider(model_id: str) -> str:
    """Map a model ID to its provider name."""
    if model_id.startswith("claude"):
        return "anthropic"
    elif model_id.startswith("gemini"):
        return "google"
    else:
        return "openai"


def _build_openai_content(msg: Dict[str, Any]) -> Any:
    """Build OpenAI message content, handling images if present."""
    if "images" not in msg or not msg["images"]:
        return msg["content"]
    # Multimodal: text + images
    parts = [{"type": "text", "text": msg["content"]}]
    for img in msg["images"]:
        parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:{img['mime_type']};base64,{img['base64_data']}"},
        })
    return parts


def _build_anthropic_content(msg: Dict[str, Any]) -> Any:
    """Build Anthropic message content, handling images if present."""
    if "images" not in msg or not msg["images"]:
        return msg["content"]
    parts = [{"type": "text", "text": msg["content"]}]
    for img in msg["images"]:
        parts.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": img["mime_type"],
                "data": img["base64_data"],
            },
        })
    return parts


def _build_google_parts(msg: Dict[str, Any]) -> list:
    """Build Google parts list, handling images if present."""
    parts = [{"text": msg["content"]}]
    if "images" in msg and msg["images"]:
        for img in msg["images"]:
            parts.append({
                "inline_data": {
                    "mime_type": img["mime_type"],
                    "data": img["base64_data"],
                }
            })
    return parts


async def _query_openai(
    model: str,
    messages: List[Dict[str, Any]],
    system_prompt: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    reasoning_effort: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Query a model via OpenAI API with optional tool-use loop."""
    if not openai_client:
        print(f"OpenAI API key not configured, skipping {model}")
        return None

    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})

    for msg in messages:
        full_messages.append({
            "role": msg["role"],
            "content": _build_openai_content(msg),
        })

    # Build tool definitions for OpenAI
    openai_tools = None
    tool_map = {}
    if tools:
        openai_tools = []
        for t in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            })
            tool_map[t.name] = t

    # Map reasoning_effort for OpenAI reasoning models (o3, o4-mini, gpt-5.2*)
    openai_reasoning = None
    if reasoning_effort and reasoning_effort != "off":
        is_reasoning_model = model.startswith("o3") or model.startswith("o4") or model.startswith("gpt-5")
        if is_reasoning_model:
            openai_reasoning = reasoning_effort  # OpenAI accepts "low", "medium", "high"

    try:
        all_tool_calls = []

        for _ in range(MAX_TOOL_ROUNDS):
            kwargs = {"model": model, "messages": full_messages}
            if openai_tools:
                kwargs["tools"] = openai_tools
            if openai_reasoning:
                kwargs["reasoning_effort"] = openai_reasoning

            response = await openai_client.chat.completions.create(**kwargs)
            choice = response.choices[0]

            # If no tool calls, we're done
            if not choice.message.tool_calls:
                usage = _extract_openai_usage(response)
                return {
                    "content": choice.message.content or "",
                    "reasoning_details": None,
                    "tool_calls": all_tool_calls if all_tool_calls else None,
                    "usage": usage,
                }

            # Process tool calls
            full_messages.append(choice.message)

            for tc in choice.message.tool_calls:
                import json
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                tool_name = tc.function.name

                # Execute tool
                from .tools.registry import execute_tool
                result = await execute_tool(tool_name, args, tool_map)

                all_tool_calls.append({
                    "tool": tool_name,
                    "args": args,
                    "result": result[:2000] if result else "",
                })

                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result or "",
                })

        # Max rounds reached — get final text response
        response = await openai_client.chat.completions.create(
            model=model, messages=full_messages
        )
        usage = _extract_openai_usage(response)
        return {
            "content": response.choices[0].message.content or "",
            "reasoning_details": None,
            "tool_calls": all_tool_calls if all_tool_calls else None,
            "usage": usage,
        }

    except Exception as e:
        print(f"Error querying OpenAI model {model}: {e}")
        return None


async def _query_anthropic(
    model: str,
    messages: List[Dict[str, Any]],
    system_prompt: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    reasoning_effort: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Query a model via Anthropic API with optional tool-use loop."""
    if not anthropic_client:
        print(f"Anthropic API key not configured, skipping {model}")
        return None

    anthropic_messages = []
    for msg in messages:
        anthropic_messages.append({
            "role": msg["role"],
            "content": _build_anthropic_content(msg),
        })

    # Build tool definitions for Anthropic
    anthropic_tools = None
    tool_map = {}
    if tools:
        anthropic_tools = []
        for t in tools:
            anthropic_tools.append({
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            })
            tool_map[t.name] = t

    kwargs = {
        "model": model,
        "messages": anthropic_messages,
        "max_tokens": 8192,
    }
    if system_prompt:
        kwargs["system"] = system_prompt
    if anthropic_tools:
        kwargs["tools"] = anthropic_tools

    # Anthropic extended thinking via adaptive budget
    if reasoning_effort and reasoning_effort != "off":
        # Map effort levels to Anthropic budget_tokens
        effort_to_budget = {"low": 2048, "medium": 8192, "high": 32768}
        budget = effort_to_budget.get(reasoning_effort, 8192)
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
        # Extended thinking requires higher max_tokens
        kwargs["max_tokens"] = max(kwargs["max_tokens"], budget + 8192)

    try:
        all_tool_calls = []

        for _ in range(MAX_TOOL_ROUNDS):
            response = await anthropic_client.messages.create(**kwargs)

            # Check for tool use blocks
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            text_blocks = [b for b in response.content if b.type == "text"]

            if not tool_use_blocks:
                text = text_blocks[0].text if text_blocks else ""
                usage = _extract_anthropic_usage(response)
                return {
                    "content": text,
                    "reasoning_details": None,
                    "tool_calls": all_tool_calls if all_tool_calls else None,
                    "usage": usage,
                }

            # Append assistant response
            kwargs["messages"].append({"role": "assistant", "content": response.content})

            # Execute tools and build results
            tool_results = []
            for block in tool_use_blocks:
                from .tools.registry import execute_tool
                result = await execute_tool(block.name, block.input, tool_map)

                all_tool_calls.append({
                    "tool": block.name,
                    "args": block.input,
                    "result": result[:2000] if result else "",
                })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result or "",
                })

            kwargs["messages"].append({"role": "user", "content": tool_results})

        # Max rounds — get final
        if anthropic_tools:
            del kwargs["tools"]
        response = await anthropic_client.messages.create(**kwargs)
        text_blocks = [b for b in response.content if b.type == "text"]
        usage = _extract_anthropic_usage(response)
        return {
            "content": text_blocks[0].text if text_blocks else "",
            "reasoning_details": None,
            "tool_calls": all_tool_calls if all_tool_calls else None,
            "usage": usage,
        }

    except Exception as e:
        print(f"Error querying Anthropic model {model}: {e}")
        return None


async def _query_google(
    model: str,
    messages: List[Dict[str, Any]],
    system_prompt: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    reasoning_effort: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Query a model via Google GenAI API with optional tool-use loop."""
    if not google_client:
        print(f"Google API key not configured, skipping {model}")
        return None

    # Convert messages to Google format
    google_contents = []
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else "user"
        parts = _build_google_parts(msg)
        google_contents.append({"role": role, "parts": parts})

    config = {}
    if system_prompt:
        config["system_instruction"] = system_prompt

    # Google thinking config for Gemini 2.5+ and 3.x models
    if reasoning_effort and reasoning_effort != "off":
        is_thinking_model = "2.5" in model or "3" in model
        if is_thinking_model:
            effort_to_budget = {"low": 2048, "medium": 8192, "high": 32768}
            budget = effort_to_budget.get(reasoning_effort, 8192)
            from google.genai.types import ThinkingConfig
            config["thinking_config"] = ThinkingConfig(thinking_budget=budget)

    # Build tool definitions for Google
    google_tools = None
    tool_map = {}
    if tools:
        from google.genai.types import Tool, FunctionDeclaration
        func_decls = []
        for t in tools:
            func_decls.append(FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=t.parameters,
            ))
            tool_map[t.name] = t
        google_tools = [Tool(function_declarations=func_decls)]

    try:
        all_tool_calls = []

        for _ in range(MAX_TOOL_ROUNDS):
            call_kwargs = {
                "model": model,
                "contents": google_contents,
                "config": config if config else None,
            }
            if google_tools:
                call_kwargs["config"] = call_kwargs.get("config") or {}
                if isinstance(call_kwargs["config"], dict):
                    call_kwargs["config"]["tools"] = google_tools

            response = await asyncio.to_thread(
                google_client.models.generate_content,
                **call_kwargs,
            )

            # Check for function calls
            has_function_call = False
            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        has_function_call = True
                        break

            if not has_function_call:
                usage = _extract_google_usage(response)
                return {
                    "content": response.text if response.text else "",
                    "reasoning_details": None,
                    "tool_calls": all_tool_calls if all_tool_calls else None,
                    "usage": usage,
                }

            # Process function calls
            google_contents.append(response.candidates[0].content)

            func_responses = []
            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    args = dict(fc.args) if fc.args else {}
                    from .tools.registry import execute_tool
                    result = await execute_tool(fc.name, args, tool_map)

                    all_tool_calls.append({
                        "tool": fc.name,
                        "args": args,
                        "result": result[:2000] if result else "",
                    })

                    from google.genai.types import Part
                    func_responses.append(
                        Part.from_function_response(
                            name=fc.name,
                            response={"result": result or ""},
                        )
                    )

            google_contents.append({"role": "user", "parts": func_responses})

        # Max rounds — get without tools
        response = await asyncio.to_thread(
            google_client.models.generate_content,
            model=model,
            contents=google_contents,
            config=config if config else None,
        )
        usage = _extract_google_usage(response)
        return {
            "content": response.text if response.text else "",
            "reasoning_details": None,
            "tool_calls": all_tool_calls if all_tool_calls else None,
            "usage": usage,
        }

    except Exception as e:
        print(f"Error querying Google model {model}: {e}")
        return None


async def query_model(
    model: str,
    messages: List[Dict[str, Any]],
    system_prompt: Optional[str] = None,
    timeout: float = 120.0,
    tools: Optional[List[Any]] = None,
    reasoning_effort: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via its provider's API.

    Args:
        model: Model identifier (e.g., "claude-opus-4-6", "gpt-4.1", "gemini-2.5-pro")
        messages: List of message dicts with 'role' and 'content' (and optional 'images')
        system_prompt: Optional system prompt
        timeout: Request timeout in seconds
        tools: Optional list of ToolDefinition objects for tool-use
        reasoning_effort: Optional reasoning effort level ("off", "low", "medium", "high")

    Returns:
        Response dict with 'content', optional 'reasoning_details' and 'tool_calls', or None if failed
    """
    provider = get_provider(model)

    if provider == "anthropic":
        query_fn = _query_anthropic(model, messages, system_prompt, tools, reasoning_effort)
    elif provider == "google":
        query_fn = _query_google(model, messages, system_prompt, tools, reasoning_effort)
    else:
        query_fn = _query_openai(model, messages, system_prompt, tools, reasoning_effort)

    try:
        return await asyncio.wait_for(query_fn, timeout=timeout)
    except asyncio.TimeoutError:
        print(f"Timeout querying model {model} after {timeout}s")
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, Any]],
    system_prompt: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    reasoning_effort: Optional[str] = None,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of model identifiers
        messages: List of message dicts to send to each model
        system_prompt: Optional system prompt
        tools: Optional list of ToolDefinition objects for tool-use
        reasoning_effort: Optional reasoning effort level ("off", "low", "medium", "high")

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    tasks = [query_model(model, messages, system_prompt, tools=tools, reasoning_effort=reasoning_effort) for model in models]
    responses = await asyncio.gather(*tasks)
    return {model: response for model, response in zip(models, responses)}
