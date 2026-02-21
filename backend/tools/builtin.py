"""Built-in tools: web search, URL fetch, calculator, code execution."""

import ast
import asyncio
import subprocess
import textwrap

from .registry import ToolDefinition, register_tool
from ..config import SEARCH_API_KEY


# --- Web Search ---

async def _web_search(query: str) -> str:
    """Search the web using SerpAPI or Brave Search API."""
    if not SEARCH_API_KEY:
        return "Web search is not configured. Set SEARCH_API_KEY environment variable."

    try:
        import aiohttp

        # Try SerpAPI first (key format: plain alphanumeric)
        url = "https://serpapi.com/search.json"
        params = {"q": query, "api_key": SEARCH_API_KEY, "num": 5}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("organic_results", [])
                    if results:
                        lines = []
                        for r in results[:5]:
                            lines.append(f"**{r.get('title', '')}**")
                            lines.append(r.get("snippet", ""))
                            lines.append(r.get("link", ""))
                            lines.append("")
                        return "\n".join(lines)
                    return "No search results found."
                return f"Search API returned status {resp.status}"
    except Exception as e:
        return f"Web search failed: {e}"


register_tool(ToolDefinition(
    name="web_search",
    description="Search the web for current information. Returns top search results with titles, snippets, and URLs.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
        },
        "required": ["query"],
    },
    handler=_web_search,
))


# --- URL Fetch ---

async def _url_fetch(url: str) -> str:
    """Fetch the content of a URL and return as text."""
    try:
        import aiohttp
        from bs4 import BeautifulSoup

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return f"Failed to fetch URL: HTTP {resp.status}"

                content_type = resp.headers.get("Content-Type", "")
                raw = await resp.text()

                if "html" in content_type.lower():
                    soup = BeautifulSoup(raw, "html.parser")
                    # Remove script/style tags
                    for tag in soup(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()
                    text = soup.get_text(separator="\n", strip=True)
                else:
                    text = raw

                # Truncate to 10K characters
                if len(text) > 10000:
                    text = text[:10000] + "\n\n[... truncated ...]"
                return text
    except Exception as e:
        return f"URL fetch failed: {e}"


register_tool(ToolDefinition(
    name="url_fetch",
    description="Fetch and read the content of a web page URL. Returns the text content of the page.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch",
            },
        },
        "required": ["url"],
    },
    handler=_url_fetch,
))


# --- Calculator ---

async def _calculator(expression: str) -> str:
    """Safely evaluate a mathematical expression."""
    try:
        # Allow only safe math operations via ast.literal_eval and simple eval
        # Whitelist safe operations
        allowed_names = {
            "abs": abs, "round": round, "min": min, "max": max,
            "pow": pow, "sum": sum, "int": int, "float": float,
        }

        # Try ast.literal_eval first for simple expressions
        try:
            result = ast.literal_eval(expression)
            return str(result)
        except (ValueError, SyntaxError):
            pass

        # Use eval with restricted builtins for math expressions
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"Calculation error: {e}"


register_tool(ToolDefinition(
    name="calculator",
    description="Evaluate a mathematical expression. Supports basic arithmetic (+, -, *, /, **, %), abs(), round(), min(), max(), pow().",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The math expression to evaluate (e.g., '2**128', '(3.14 * 5**2)')",
            },
        },
        "required": ["expression"],
    },
    handler=_calculator,
))


# --- Code Execution ---

async def _code_execution(code: str, language: str = "python") -> str:
    """Execute code in a subprocess with a timeout."""
    if language != "python":
        return f"Only Python execution is supported. Got: {language}"

    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                "python3", "-c", code,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ),
            timeout=10.0,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)

        output = ""
        if stdout:
            output += stdout.decode("utf-8", errors="replace")
        if stderr:
            output += "\nSTDERR:\n" + stderr.decode("utf-8", errors="replace")

        if not output.strip():
            output = "(no output)"

        # Truncate
        if len(output) > 5000:
            output = output[:5000] + "\n\n[... truncated ...]"

        return output
    except asyncio.TimeoutError:
        return "Code execution timed out (10s limit)"
    except Exception as e:
        return f"Code execution failed: {e}"


register_tool(ToolDefinition(
    name="code_execution",
    description="Execute Python code and return the output. Code runs in an isolated subprocess with a 10-second timeout.",
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute",
            },
            "language": {
                "type": "string",
                "description": "Programming language (currently only 'python' is supported)",
                "default": "python",
            },
        },
        "required": ["code"],
    },
    handler=_code_execution,
))
