"""Built-in simple connectors: web search prequery, URL content, REST API."""

from .registry import ConnectorDefinition, register_connector
from ..config import SEARCH_API_KEY


# --- Web Search Prequery ---

async def _web_search_prequery(query: str, max_results: int = 5) -> str:
    """Search the web before the query and inject results as context."""
    if not SEARCH_API_KEY:
        return "Web search prequery not available — SEARCH_API_KEY not configured."

    try:
        import aiohttp

        url = "https://serpapi.com/search.json"
        params = {"q": query, "api_key": SEARCH_API_KEY, "num": max_results}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return f"Search API returned status {resp.status}"
                data = await resp.json()
                results = data.get("organic_results", [])
                if not results:
                    return "No search results found."
                lines = []
                for r in results[:max_results]:
                    lines.append(f"Title: {r.get('title', '')}")
                    lines.append(f"Snippet: {r.get('snippet', '')}")
                    lines.append(f"URL: {r.get('link', '')}")
                    lines.append("")
                return "\n".join(lines)
    except Exception as e:
        return f"Web search prequery failed: {e}"


register_connector(ConnectorDefinition(
    name="web_search_prequery",
    description="Search the web before sending your query. Results are injected as context for all council models.",
    connector_type="simple",
    config_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query to run before the council query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to include",
                "default": 5,
            },
        },
        "required": ["query"],
    },
    fetcher=_web_search_prequery,
))


# --- URL Content ---

async def _url_content(url: str) -> str:
    """Fetch a URL and inject its text content as context."""
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
                    for tag in soup(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()
                    text = soup.get_text(separator="\n", strip=True)
                else:
                    text = raw

                if len(text) > 15000:
                    text = text[:15000] + "\n\n[... truncated ...]"
                return text
    except Exception as e:
        return f"URL content fetch failed: {e}"


register_connector(ConnectorDefinition(
    name="url_content",
    description="Fetch a web page and inject its content as context for all council models.",
    connector_type="simple",
    config_schema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch content from",
            },
        },
        "required": ["url"],
    },
    fetcher=_url_content,
))


# --- REST API ---

async def _rest_api(endpoint: str, method: str = "GET", headers: dict = None) -> str:
    """Fetch data from a REST API endpoint."""
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            req_headers = headers or {}
            async with session.request(
                method, endpoint, headers=req_headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                text = await resp.text()
                if len(text) > 15000:
                    text = text[:15000] + "\n\n[... truncated ...]"
                return f"Status: {resp.status}\n\n{text}"
    except Exception as e:
        return f"REST API fetch failed: {e}"


register_connector(ConnectorDefinition(
    name="rest_api",
    description="Fetch data from a REST API endpoint and inject the response as context.",
    connector_type="simple",
    config_schema={
        "type": "object",
        "properties": {
            "endpoint": {
                "type": "string",
                "description": "REST API endpoint URL",
            },
            "method": {
                "type": "string",
                "description": "HTTP method (GET, POST, etc.)",
                "default": "GET",
            },
            "headers": {
                "type": "object",
                "description": "Optional HTTP headers as key-value pairs",
                "default": {},
            },
        },
        "required": ["endpoint"],
    },
    fetcher=_rest_api,
))
