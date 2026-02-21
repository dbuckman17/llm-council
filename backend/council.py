"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple, Optional
from .providers import query_models_parallel, query_model
from .config import MODEL_PRICING


def calculate_cost(model: str, usage: dict) -> float:
    """Calculate cost in USD for a model query based on token usage."""
    if not usage:
        return 0.0
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return 0.0
    input_price, output_price = pricing
    input_cost = (usage.get("input_tokens", 0) / 1_000_000) * input_price
    output_cost = (usage.get("output_tokens", 0) / 1_000_000) * output_price
    return input_cost + output_cost


async def stage1_collect_responses(
    user_query: str,
    council_models: List[str],
    system_prompt: Optional[str] = None,
    file_context: Optional[str] = None,
    image_attachments: Optional[List[Dict[str, str]]] = None,
    tools: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question
        council_models: List of model identifiers to query
        system_prompt: Optional system prompt for the models
        file_context: Optional text context from uploaded files
        image_attachments: Optional list of {mime_type, base64_data} for vision
        tools: Optional list of ToolDefinition objects for tool-use

    Returns:
        List of dicts with 'model', 'response', and optional 'tool_calls' keys
    """
    # Build the user message content, prepending file context if present
    content = user_query
    if file_context:
        content = f"[ATTACHED FILES]\n{file_context}\n[END ATTACHED FILES]\n\n{user_query}"

    user_msg: Dict[str, Any] = {"role": "user", "content": content}
    if image_attachments:
        user_msg["images"] = image_attachments

    messages = [user_msg]

    # Query all models in parallel
    responses = await query_models_parallel(council_models, messages, system_prompt, tools=tools)

    # Format results
    stage1_results = []
    for model, response in responses.items():
        if response is not None:  # Only include successful responses
            usage = response.get('usage', {})
            cost = calculate_cost(model, usage)
            result = {
                "model": model,
                "response": response.get('content', ''),
                "usage": usage,
                "cost": cost,
            }
            if response.get('tool_calls'):
                result["tool_calls"] = response['tool_calls']
            stage1_results.append(result)

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    council_models: List[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        council_models: List of model identifiers to use for ranking

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel (no system prompt for stage 2)
    responses = await query_models_parallel(council_models, messages)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            usage = response.get('usage', {})
            cost = calculate_cost(model, usage)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed,
                "usage": usage,
                "cost": cost,
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    chairman_model: str,
    previous_iteration: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2
        chairman_model: Model identifier for the chairman
        previous_iteration: Optional dict with previous run context for re-analysis

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}"""

    if previous_iteration:
        chairman_prompt += f"""

PREVIOUS ITERATION CONTEXT:
This is a re-analysis. In the previous iteration:
- Previous Query: {previous_iteration.get('query', 'N/A')}
- Previous System Prompt: {previous_iteration.get('system_prompt', 'None')}
- Previous Synthesis: {previous_iteration.get('stage3_response', 'N/A')}
- Critique of Previous Analysis: {previous_iteration.get('critique', 'N/A')}

Consider how the current responses compare to the previous iteration. Note improvements or regressions."""

    chairman_prompt += """

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model (no system prompt for stage 3)
    response = await query_model(chairman_model, messages)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": chairman_model,
            "response": "Error: Unable to generate final synthesis.",
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "cost": 0.0,
        }

    usage = response.get('usage', {})
    cost = calculate_cost(chairman_model, usage)
    return {
        "model": chairman_model,
        "response": response.get('content', ''),
        "usage": usage,
        "cost": cost,
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


def parse_stage4_response(text: str) -> Dict[str, str]:
    """
    Parse the Stage 4 self-reflection response into structured sections.

    Args:
        text: Raw response text from the chairman

    Returns:
        Dict with 'critique', 'comparison', 'suggested_system_prompt', 'suggested_query'
    """
    result = {
        "critique": "",
        "comparison": "",
        "suggested_system_prompt": "",
        "suggested_query": "",
    }

    # Define section headers to look for
    sections = [
        ("CRITIQUE:", "critique"),
        ("COMPARISON:", "comparison"),
        ("SUGGESTED_SYSTEM_PROMPT:", "suggested_system_prompt"),
        ("SUGGESTED_QUERY:", "suggested_query"),
    ]

    # Find all section positions
    positions = []
    for header, key in sections:
        idx = text.find(header)
        if idx != -1:
            positions.append((idx, header, key))

    if not positions:
        # Fallback: entire response goes into critique
        result["critique"] = text.strip()
        return result

    # Sort by position
    positions.sort(key=lambda x: x[0])

    # Extract each section's content
    for i, (pos, header, key) in enumerate(positions):
        start = pos + len(header)
        if i + 1 < len(positions):
            end = positions[i + 1][0]
        else:
            end = len(text)
        result[key] = text[start:end].strip()

    return result


async def stage4_self_reflection(
    user_query: str,
    system_prompt: Optional[str],
    stage1_results: List[Dict[str, Any]],
    stage3_result: Dict[str, Any],
    chairman_model: str,
    previous_iteration: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Stage 4: Chairman self-reflects on the analysis and suggests improvements.

    Args:
        user_query: The original user query
        system_prompt: The system prompt used (if any)
        stage1_results: Individual model responses from Stage 1
        stage3_result: The final synthesis from Stage 3
        chairman_model: Model identifier for the chairman
        previous_iteration: Optional dict with previous run context

    Returns:
        Dict with model, critique, comparison, suggested_system_prompt, suggested_query, raw_response
    """
    is_rerun = previous_iteration is not None

    stage1_summary = "\n".join([
        f"- {r['model']}: {r['response'][:200]}..."
        for r in stage1_results
    ])

    reflection_prompt = f"""You are the Chairman of an LLM Council. You just completed a full analysis. Now reflect on how it could be improved.

Original Query: {user_query}
System Prompt Used: {system_prompt or 'None'}

Stage 1 Responses (summarized):
{stage1_summary}

Stage 3 Final Synthesis:
{stage3_result.get('response', '')}"""

    if is_rerun:
        reflection_prompt += f"""

PREVIOUS ITERATION:
- Previous Query: {previous_iteration.get('query', 'N/A')}
- Previous System Prompt: {previous_iteration.get('system_prompt', 'None')}
- Previous Synthesis: {previous_iteration.get('stage3_response', 'N/A')}"""

    reflection_prompt += """

Provide your self-reflection using EXACTLY these section headers:

CRITIQUE:
What were the weaknesses or gaps in this analysis? What could the council have done better? Be specific and actionable.
"""

    if is_rerun:
        reflection_prompt += """
COMPARISON:
How does this iteration compare to the previous one? What improved? What regressed or remained unaddressed?
"""

    reflection_prompt += """
SUGGESTED_SYSTEM_PROMPT:
Write an improved system prompt that would help the council models produce better responses. If the current system prompt was good, refine it. If none was used, suggest one. Output ONLY the system prompt text.

SUGGESTED_QUERY:
Write an improved version of the user's query that would elicit better responses. Make it more specific, clearer, or better structured. Output ONLY the query text."""

    messages = [{"role": "user", "content": reflection_prompt}]
    response = await query_model(chairman_model, messages)

    if response is None:
        return {
            "model": chairman_model,
            "critique": "Error: Unable to generate self-reflection.",
            "comparison": "",
            "suggested_system_prompt": system_prompt or "",
            "suggested_query": user_query,
            "raw_response": "",
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "cost": 0.0,
        }

    raw_text = response.get('content', '')
    parsed = parse_stage4_response(raw_text)
    usage = response.get('usage', {})
    cost = calculate_cost(chairman_model, usage)

    return {
        "model": chairman_model,
        "critique": parsed["critique"],
        "comparison": parsed["comparison"],
        "suggested_system_prompt": parsed["suggested_system_prompt"],
        "suggested_query": parsed["suggested_query"],
        "raw_response": raw_text,
        "usage": usage,
        "cost": cost,
    }


async def generate_conversation_title(user_query: str, model: str = "gemini-2.0-flash") -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message
        model: Model to use for title generation

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    response = await query_model(model, messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(
    user_query: str,
    council_models: List[str],
    chairman_model: str,
    system_prompt: Optional[str] = None,
) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question
        council_models: List of model identifiers for the council
        chairman_model: Model identifier for the chairman
        system_prompt: Optional system prompt (used in Stage 1 only)

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query, council_models, system_prompt)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results, council_models)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        chairman_model,
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata
