"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# Provider API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Available models organized by provider
AVAILABLE_MODELS = {
    "Anthropic": [
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    ],
    "OpenAI": [
        "gpt-5.2-pro",
        "gpt-5.2",
        "gpt-5-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "o4-mini",
        "o3",
    ],
    "Google": [
        "gemini-3.1-pro-preview",
        "gemini-3-flash-preview",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ],
}

# Pricing per 1M tokens (USD): {model_id: (input_price, output_price)}
MODEL_PRICING = {
    # Anthropic
    "claude-opus-4-6":          (5.00, 25.00),
    "claude-sonnet-4-6":        (3.00, 15.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    # OpenAI
    "gpt-5.2-pro":              (21.00, 168.00),
    "gpt-5.2":                  (1.75, 14.00),
    "gpt-5-mini":               (0.25, 2.00),
    "gpt-4.1":                  (2.00, 8.00),
    "gpt-4.1-mini":             (0.40, 1.60),
    "gpt-4.1-nano":             (0.10, 0.40),
    "o4-mini":                  (1.10, 4.40),
    "o3":                       (2.00, 8.00),
    # Google
    "gemini-3.1-pro-preview":   (2.00, 12.00),
    "gemini-3-flash-preview":   (0.50, 3.00),
    "gemini-2.5-pro":           (1.25, 10.00),
    "gemini-2.5-flash":         (0.30, 2.50),
    "gemini-2.0-flash":         (0.10, 0.40),
}

# GCP / deployment settings
DATABASE_URL = os.getenv("DATABASE_URL")  # postgres DSN (None = use JSON files)
USE_VERTEX_AI = os.getenv("USE_VERTEX_AI", "false").lower() == "true"
GCP_PROJECT = os.getenv("GCP_PROJECT")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")

# Data directory for conversation storage (JSON mode only)
DATA_DIR = "data/conversations"

# File uploads directory
FILES_DIR = "data/files"

# Optional: search API key for tool-use web search (SerpAPI or Brave)
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
