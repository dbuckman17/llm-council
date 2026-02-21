# CLAUDE.md - Technical Notes for LLM Council

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

LLM Council is a 3-stage deliberation system where multiple LLMs collaboratively answer user questions. The key innovation is anonymized peer review in Stage 2, preventing models from playing favorites.

## Architecture

### Backend Structure (`backend/`)

**`config.py`**
- Contains `AVAILABLE_MODELS` dict organized by provider (Anthropic, OpenAI, Google)
- Uses environment variables `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` from `.env`
- Backend runs on **port 8001** (NOT 8000 - user had another app on 8000)
- Models are bare IDs (e.g., `claude-opus-4-6`, `gpt-4.1`, `gemini-2.5-pro`) — no provider prefix

**`providers.py`** — Provider API Layer
- Uses official SDKs: `openai`, `anthropic`, `google-genai`
- SDK clients instantiated at module level for connection reuse
- `get_provider(model_id)`: Maps model ID to provider name via prefix matching
- `query_model()`: Routes to correct provider, returns `{'content': str, 'reasoning_details': optional, 'tool_calls': optional}` or `None`
- `query_models_parallel()`: Parallel queries using `asyncio.gather()`
- **Multimodal support**: Messages can include `images` key with `{mime_type, base64_data}` dicts. Each `_query_*` function transforms to provider-specific format (OpenAI `image_url`, Anthropic `image/source`, Google `inline_data`).
- **Tool-use loops**: Each `_query_*` function accepts optional `tools` param. If models return tool calls, executes them and loops (max 5 rounds). Returns accumulated `tool_calls` list.
- Provider-specific details:
  - **OpenAI**: system prompt as system message, tools as `functions`, tool results as `role: "tool"` messages
  - **Anthropic**: system prompt as top-level `system` kwarg, `max_tokens=8192`, tools as `tool_use`/`tool_result` blocks
  - **Google**: `asyncio.to_thread()` wrapper around sync SDK, system prompt as `system_instruction`, tools as `FunctionDeclaration`
- Graceful degradation: returns None on failure, logs error, continues

**`templates.py`** — System Prompt Templates
- `SYSTEM_PROMPT_TEMPLATES` list with pre-built templates (Expert Coder, Research Analyst, Creative Writer, Debate Coach, Data Scientist, Custom)
- Each template: `{id, name, description, system_prompt, configurable_fields[]}`
- `{{placeholder}}` syntax in prompts, substituted by `render_template(template_id, field_values)`

**`files.py`** — File Upload & Text Extraction
- `ConversationFile` dataclass with metadata
- File storage: `data/files/{conversation_id}/{file_id}_{filename}`
- Text extraction: UTF-8 for text/code, `pypdf` for PDF, `python-docx` for DOCX, `openpyxl` for XLSX
- Images stored for base64 vision pass-through (max 2MB)
- Dual-mode metadata: JSON manifest (`_manifest.json`) or Postgres `conversation_files` table
- `get_file_content_for_context()` returns `(text_context, image_attachments[])` for Stage 1

**`tools/`** — Tool-Use Package
- `registry.py`: `ToolDefinition` dataclass, `TOOL_REGISTRY` dict, `register_tool()`, `get_enabled_tools()`, `execute_tool()`
- `builtin.py`: Built-in tools registered on import — `web_search`, `url_fetch`, `calculator`, `code_execution`
- Tools are invoked during Stage 1 via provider tool-use loops

**`connectors/`** — External Connectors Package
- `registry.py`: `ConnectorDefinition` dataclass, `CONNECTOR_REGISTRY` dict, `register_connector()`, `run_connector()`
- `builtin.py`: Built-in connectors — `web_search_prequery`, `url_content`, `rest_api`
- `oauth.py`: OAuth token storage scaffolding for future OAuth-based connectors
- Connectors run BEFORE Stage 1, injecting data as context alongside file content

**`council.py`** — The Core Logic
- All stage functions accept `council_models` and `chairman_model` as params (no config constants)
- `system_prompt` passed to Stage 1 only (Stage 2/3 have their own specialized prompts)
- `stage1_collect_responses()`: Parallel queries to all council models. Accepts `file_context`, `image_attachments`, and `tools` params.
- `stage2_collect_rankings()`:
  - Anonymizes responses as "Response A, B, C, etc."
  - Creates `label_to_model` mapping for de-anonymization
  - Prompts models to evaluate and rank (with strict format requirements)
  - Returns tuple: (rankings_list, label_to_model_dict)
- `stage3_synthesize_final()`: Chairman synthesizes from all responses + rankings
- `parse_ranking_from_text()`: Extracts "FINAL RANKING:" section
- `calculate_aggregate_rankings()`: Computes average rank position across all peer evaluations
- `generate_conversation_title()`: Accepts a model param, defaults to `gemini-2.0-flash`

**`storage.py`**
- JSON-based conversation storage in `data/conversations/`
- Each conversation: `{id, created_at, title, messages[]}`
- Assistant messages contain: `{role, stage1, stage2, stage3}`
- Note: metadata (label_to_model, aggregate_rankings) is NOT persisted to storage

**`main.py`**
- FastAPI app with CORS enabled for localhost:5173 and localhost:3000
- `GET /api/models` — returns `AVAILABLE_MODELS` for frontend dropdowns
- `GET /api/templates` — returns system prompt templates
- `GET /api/tools` — returns available tools from registry
- `GET /api/connectors` — returns available connectors from registry
- `POST /api/optimize-prompt` — takes `{prompt, model}`, returns `{optimized_prompt}`
- `POST /api/conversations/{id}/message` — accepts `council_models`, `chairman_model`, `system_prompt`
- `POST /api/conversations/{id}/message/stream` — accepts `council_models`, `chairman_model`, `system_prompt`, `enabled_tools`, `enabled_connectors`, returns SSE events
- `POST /api/conversations/{id}/files` — multipart file upload
- `GET /api/conversations/{id}/files` — list conversation files
- `DELETE /api/conversations/{id}/files/{file_id}` — delete a file
- `GET /api/conversations/{id}/files/{file_id}` — download a file

### Frontend Structure (`frontend/src/`)

**`api.js`**
- `getModels()`, `getTemplates()`, `getTools()`, `getConnectors()` — fetches config data from backend
- `uploadFiles()`, `listFiles()`, `deleteFile()` — file management per conversation
- `optimizePrompt(prompt, model)` — calls optimize endpoint
- `sendMessageStream()` — includes `council_models`, `chairman_model`, `system_prompt`, `enabled_tools`, `enabled_connectors`

**`App.jsx`**
- State: `availableModels`, `selectedCouncilModels`, `chairmanModel`, `systemPrompt`, `templates`, `conversationFiles`, `availableTools`, `enabledTools`, `availableConnectors`, `enabledConnectors`
- Fetches models, templates, tools, connectors on mount; loads files when switching conversations
- Passes all state to ChatInterface

**`components/ChatInterface.jsx`**
- Expanded input area with:
  - ModelSelector (provider columns + chairman dropdown)
  - TemplateSelector (skill template dropdown + config fields)
  - System prompt textarea (optional, 2 rows)
  - ToolSelector (checkbox list of available tools)
  - ConnectorPanel (toggle + config form per connector)
  - FileUpload (drag & drop + file list)
  - Query textarea (3 rows)
  - Optimize Prompt button with model selector
  - Send button
  - Collapsible Prompting Tips
- Enter to send, Shift+Enter for new line

**`components/ModelSelector.jsx`**
- Three provider columns with checkboxes for council member selection
- Separate chairman dropdown (single select, all models)

**`components/PromptingTips.jsx`**
- Collapsible section, starts collapsed
- Static bullet list of prompting best practices

**`components/TemplateSelector.jsx`**
- Dropdown for skill template selection with configurable fields
- Selecting a template populates the system prompt; fields update via `{{placeholder}}` substitution

**`components/FileUpload.jsx`**
- Drag & drop zone + file picker + file list with remove buttons
- Uploads files via multipart FormData to conversation endpoint

**`components/ToolSelector.jsx`**
- Checkbox list of available tools with names and descriptions

**`components/ConnectorPanel.jsx`**
- Toggle + expandable config form per connector
- Config fields generated dynamically from connector's JSON Schema

**`components/Stage1.jsx`**
- Tab view of individual model responses
- ReactMarkdown rendering with markdown-content wrapper
- Collapsible "Tool Calls (N)" section showing tool name, args, and result for each call

**`components/Stage2.jsx`**
- Tab view showing RAW evaluation text from each model
- De-anonymization happens CLIENT-SIDE for display
- Shows "Extracted Ranking" below each evaluation
- Aggregate rankings with average position and vote count

**`components/Stage3.jsx`**
- Final synthesized answer from chairman
- Green-tinted background (#f0fff0) to highlight conclusion

**Styling (`*.css`)**
- Light mode theme (not dark mode)
- Primary color: #4a90e2 (blue)
- Global markdown styling in `index.css` with `.markdown-content` class
- 12px padding on all markdown content

## Key Design Decisions

### Direct Provider APIs (not OpenRouter)
- Uses official SDKs for OpenAI, Anthropic, and Google directly
- Each provider's API key is configured independently
- Model IDs are bare (e.g., `claude-opus-4-6` not `anthropic/claude-opus-4-6`)
- Missing API keys are handled gracefully (models from that provider are skipped)

### Dynamic Model Selection
- Models are selected per-query in the frontend UI
- Council members chosen via checkboxes, chairman via dropdown
- No hardcoded model assignments — fully user-configurable

### Stage 2 Prompt Format
The Stage 2 prompt is very specific to ensure parseable output:
```
1. Evaluate each response individually first
2. Provide "FINAL RANKING:" header
3. Numbered list format: "1. Response C", "2. Response A", etc.
4. No additional text after ranking section
```

### De-anonymization Strategy
- Models receive: "Response A", "Response B", etc.
- Backend creates mapping: `{"Response A": "claude-opus-4-6", ...}`
- Frontend displays model names in **bold** for readability
- Users see explanation that original evaluation used anonymous labels

### Error Handling Philosophy
- Continue with successful responses if some models fail (graceful degradation)
- Never fail the entire request due to single model failure
- Log errors but don't expose to user unless all models fail

## Important Implementation Details

### Relative Imports
All backend modules use relative imports (e.g., `from .config import ...`). Run as `python -m backend.main` from project root.

### Port Configuration
- Backend: 8001 (changed from 8000 to avoid conflict)
- Frontend: 5173 (Vite default)
- Update both `backend/main.py` and `frontend/src/api.js` if changing

### Markdown Rendering
All ReactMarkdown components must be wrapped in `<div className="markdown-content">`.

### Environment Variables
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...
SEARCH_API_KEY=...          # Optional: SerpAPI key for web_search tool and web_search_prequery connector
```

## Common Gotchas

1. **Module Import Errors**: Always run backend as `python -m backend.main` from project root
2. **CORS Issues**: Frontend must match allowed origins in `main.py` CORS middleware
3. **Ranking Parse Failures**: If models don't follow format, fallback regex extracts any "Response X" patterns
4. **Missing Metadata**: Metadata is ephemeral (not persisted), only available in API responses
5. **Missing API Keys**: Provider SDK clients are None if key not set; those models silently fail
6. **python-multipart**: Required by FastAPI for file uploads — without it, `UploadFile` params fail silently
7. **Tool-use timeout**: Tool loops can extend Stage 1 time. `MAX_TOOL_ROUNDS=5` and existing 120s timeout in `query_model()`
8. **Image base64 size**: Images capped at 2MB in `files.py` (`MAX_IMAGE_BYTES`)
9. **Code execution security**: `code_execution` tool runs subprocess — in production must be sandboxed

## Data Flow Summary

```
User selects council models + chairman + optional system prompt/template
User optionally enables tools, connectors, and uploads files
    ↓
User Query
    ↓
Connectors run (pre-query web search, URL fetch, REST API) → connector context
    ↓
File context extracted (text from docs, base64 from images) → file context
    ↓
Stage 1: Parallel queries (with system prompt + file/connector context + tools) → [individual responses + tool call logs]
    ↓
Stage 2: Anonymize → Parallel ranking queries (no system prompt) → [evaluations + parsed rankings]
    ↓
Aggregate Rankings Calculation → [sorted by avg position]
    ↓
Stage 3: Chairman synthesis with full context (no system prompt)
    ↓
Stage 4: Chairman self-reflection → [critique, suggestions]
    ↓
Return: {stage1, stage2, stage3, stage4, metadata}
    ↓
Frontend: Display with tabs + tool calls + validation UI
```

The entire flow is async/parallel where possible to minimize latency.
