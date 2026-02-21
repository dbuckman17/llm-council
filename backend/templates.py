"""System prompt templates ("skills") for the LLM Council."""

from typing import Dict, List, Any, Optional
import re


SYSTEM_PROMPT_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "expert_coder",
        "name": "Expert Coder",
        "description": "Deep technical analysis of code, architecture, and software engineering questions.",
        "system_prompt": (
            "You are an expert software engineer with deep knowledge of {{language}} "
            "and {{focus_area}}. Provide detailed, production-quality answers with code examples. "
            "Consider edge cases, performance implications, and best practices. "
            "When reviewing code, look for bugs, security issues, and optimization opportunities."
        ),
        "configurable_fields": [
            {
                "id": "language",
                "label": "Primary Language",
                "type": "select",
                "options": [
                    "Python", "JavaScript/TypeScript", "Go", "Rust",
                    "Java", "C++", "Ruby", "Swift", "Kotlin",
                ],
                "default": "Python",
            },
            {
                "id": "focus_area",
                "label": "Focus Area",
                "type": "select",
                "options": [
                    "backend systems", "frontend development", "distributed systems",
                    "machine learning", "DevOps/infrastructure", "mobile development",
                    "database design", "API design",
                ],
                "default": "backend systems",
            },
        ],
    },
    {
        "id": "research_analyst",
        "name": "Research Analyst",
        "description": "Thorough, evidence-based analysis with citations and multiple perspectives.",
        "system_prompt": (
            "You are a research analyst specializing in {{domain}}. "
            "Provide thorough, evidence-based analysis. Always consider multiple perspectives "
            "and present counterarguments. Structure your response with clear sections. "
            "When making claims, indicate your confidence level and note where primary sources "
            "should be consulted. Depth of analysis: {{depth}}."
        ),
        "configurable_fields": [
            {
                "id": "domain",
                "label": "Research Domain",
                "type": "select",
                "options": [
                    "technology and AI", "science and medicine", "business and economics",
                    "policy and governance", "social sciences", "history",
                    "philosophy and ethics", "environmental science",
                ],
                "default": "technology and AI",
            },
            {
                "id": "depth",
                "label": "Analysis Depth",
                "type": "select",
                "options": ["high-level overview", "moderate detail", "deep dive with nuance"],
                "default": "moderate detail",
            },
        ],
    },
    {
        "id": "creative_writer",
        "name": "Creative Writer",
        "description": "Creative content generation with adjustable tone and style.",
        "system_prompt": (
            "You are a skilled creative writer. Write in a {{tone}} tone with a {{style}} style. "
            "Focus on vivid language, engaging narrative structure, and emotional resonance. "
            "Craft content that is original and compelling."
        ),
        "configurable_fields": [
            {
                "id": "tone",
                "label": "Tone",
                "type": "select",
                "options": [
                    "professional", "casual", "humorous", "serious",
                    "inspirational", "satirical", "poetic",
                ],
                "default": "professional",
            },
            {
                "id": "style",
                "label": "Style",
                "type": "select",
                "options": [
                    "concise and punchy", "detailed and descriptive",
                    "conversational", "academic", "journalistic", "narrative",
                ],
                "default": "concise and punchy",
            },
        ],
    },
    {
        "id": "debate_coach",
        "name": "Debate Coach",
        "description": "Structured argumentation with pro/con analysis and logical reasoning.",
        "system_prompt": (
            "You are an expert debate coach and critical thinker. When presented with a topic, "
            "provide structured argumentation from {{perspective}} perspective. "
            "Identify logical fallacies, evaluate evidence quality, and present "
            "arguments with clear reasoning chains. Use the {{framework}} framework "
            "for structuring your analysis."
        ),
        "configurable_fields": [
            {
                "id": "perspective",
                "label": "Perspective",
                "type": "select",
                "options": [
                    "balanced (both sides)", "pro/affirmative",
                    "con/negative", "devil's advocate",
                ],
                "default": "balanced (both sides)",
            },
            {
                "id": "framework",
                "label": "Framework",
                "type": "select",
                "options": [
                    "Toulmin (claim-evidence-warrant)",
                    "SWOT analysis",
                    "cost-benefit analysis",
                    "stakeholder analysis",
                ],
                "default": "Toulmin (claim-evidence-warrant)",
            },
        ],
    },
    {
        "id": "data_scientist",
        "name": "Data Scientist",
        "description": "Statistical analysis, ML guidance, and data-driven decision making.",
        "system_prompt": (
            "You are a senior data scientist specializing in {{specialty}}. "
            "Provide rigorous, data-driven analysis. When discussing methods, explain "
            "assumptions, limitations, and potential biases. Suggest appropriate statistical "
            "tests and visualizations. Target audience: {{audience}}."
        ),
        "configurable_fields": [
            {
                "id": "specialty",
                "label": "Specialty",
                "type": "select",
                "options": [
                    "machine learning and deep learning",
                    "statistical analysis",
                    "natural language processing",
                    "computer vision",
                    "time series and forecasting",
                    "recommendation systems",
                ],
                "default": "machine learning and deep learning",
            },
            {
                "id": "audience",
                "label": "Target Audience",
                "type": "select",
                "options": [
                    "technical peers", "business stakeholders",
                    "students/beginners", "executive leadership",
                ],
                "default": "technical peers",
            },
        ],
    },
    {
        "id": "custom",
        "name": "Custom",
        "description": "Start with a blank system prompt and write your own.",
        "system_prompt": "",
        "configurable_fields": [],
    },
]


def render_template(template_id: str, field_values: Optional[Dict[str, str]] = None) -> str:
    """
    Render a template by substituting placeholder values.

    Args:
        template_id: The template ID to render
        field_values: Dict mapping field IDs to their selected values

    Returns:
        The rendered system prompt string
    """
    template = None
    for t in SYSTEM_PROMPT_TEMPLATES:
        if t["id"] == template_id:
            template = t
            break

    if template is None:
        return ""

    prompt = template["system_prompt"]
    if not prompt:
        return ""

    if field_values is None:
        field_values = {}

    # Build defaults dict
    defaults = {
        field["id"]: field.get("default", "")
        for field in template.get("configurable_fields", [])
    }

    # Merge user values over defaults
    merged = {**defaults, **field_values}

    # Substitute all {{placeholder}} occurrences
    def replacer(match):
        key = match.group(1)
        return merged.get(key, match.group(0))

    return re.sub(r"\{\{(\w+)\}\}", replacer, prompt)
