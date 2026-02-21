# LLM Council

![llmcouncil](header.jpg)

Instead of asking a question to a single LLM, group them into your **LLM Council**. This is a local web app that sends your query to multiple LLM providers simultaneously, has them review and rank each other's work via anonymized peer evaluation, and then a Chairman LLM synthesizes the final answer.

## How It Works

When you submit a query, the council runs a **4-stage deliberation pipeline**:

1. **Stage 1 — Individual Responses**: Your query is sent to all selected council models in parallel. Each model responds independently. Responses are shown in a tab view so you can compare them side by side.

2. **Stage 2 — Anonymized Peer Review**: Each model receives all other models' responses with anonymized labels ("Response A", "Response B", etc.) to prevent favoritism. Each model evaluates and ranks the responses. Aggregate rankings are computed across all evaluators.

3. **Stage 3 — Chairman Synthesis**: The designated Chairman model takes all individual responses and peer rankings, then synthesizes a single comprehensive answer representing the council's collective wisdom.

4. **Stage 4 — Self-Reflection**: The Chairman critiques its own synthesis, comparing it to the individual responses. It suggests an improved system prompt and refined query, which you can edit and use to **re-run the entire pipeline** in an iterative feedback loop.

## Features

### Multi-Provider Model Support

16 models across three providers, all selectable in the UI:

| Anthropic | OpenAI | Google |
|-----------|--------|--------|
| Claude Opus 4.6 | GPT-5.2 Pro | Gemini 3.1 Pro |
| Claude Sonnet 4.6 | GPT-5.2 | Gemini 3 Flash |
| Claude Haiku 4.5 | GPT-5 Mini | Gemini 2.5 Pro |
| | GPT-4.1 / Mini / Nano | Gemini 2.5 Flash |
| | o4-mini, o3 | Gemini 2.0 Flash |

- **Council members**: Select any combination via checkboxes (organized by provider)
- **Chairman**: Choose any single model from a dropdown
- Models from providers without a configured API key are gracefully skipped

### System Prompt Templates ("Skills")

Pre-built system prompt templates with configurable fields:

- **Expert Coder** — with selectable language and focus area
- **Research Analyst** — with domain specialization
- **Creative Writer** — with genre and style options
- **Debate Coach** — for structured argumentation
- **Data Scientist** — for analytical queries
- **Custom** — write your own from scratch

Templates use `{{placeholder}}` substitution. Select a template, configure its fields, and the system prompt populates automatically (editable before sending).

### Per-Conversation File Uploads

Upload files that provide persistent context for all messages in a conversation:

- **Supported formats**: Text/code, PDF, DOCX, XLSX, CSV, JSON, Markdown
- **Image vision**: PNG, JPG, GIF, WebP — images are sent as base64 to all providers using their native multimodal APIs
- **Text extraction**: PDFs via `pypdf`, Word docs via `python-docx`, spreadsheets via `openpyxl`
- **Drag & drop**: Drop files directly onto the upload zone or click to browse
- File content is prepended to your query as context; images are passed through for vision-capable models

### Tool-Use (Stage 1)

Models can call tools during Stage 1 to gather information:

- **Web Search** — search the web via SerpAPI/Brave (requires `SEARCH_API_KEY`)
- **URL Fetch** — fetch and extract text from web pages
- **Calculator** — evaluate mathematical expressions safely
- **Code Execution** — run Python code in a sandboxed subprocess

Tool calls are displayed in a collapsible section within each model's Stage 1 response tab, showing the tool name, arguments, and results.

### External Connectors

Inject external data as context *before* Stage 1 runs:

- **Web Search Pre-query** — automatically search the web and inject results as context
- **URL Content** — fetch a URL and inject its content
- **REST API** — call any REST endpoint and inject the response

Each connector has a toggleable config panel with its own parameters.

### Cost Tracking

Real-time cost estimation for every query:

- Per-stage cost breakdown (Stage 1, 2, 3, 4)
- Per-model cost breakdown
- Total workflow cost
- Based on token usage extracted from each provider's response and configurable pricing table

### Prompt Optimization

Click "Optimize Prompt" before sending to have a selected model rewrite your query for clarity, specificity, and structure. Choose which model performs the optimization.

### Iterative Re-run Loop

After Stage 4, the Chairman suggests improvements. You can:
- Edit the suggested system prompt and query
- Toggle whether to provide previous iteration context to council members
- Click "Re-run Analysis" to start a new deliberation cycle with the refined inputs

### Dual-Mode Storage

- **Default**: JSON files in `data/conversations/` — zero setup, works locally
- **Optional**: PostgreSQL via `DATABASE_URL` environment variable — for production deployments with `asyncpg` connection pooling

### Deployment Ready

Includes Docker support:
- `Dockerfile.backend` and `Dockerfile.frontend`
- `nginx.conf` for frontend serving
- `.dockerignore` for clean builds
- Configurable CORS origins via `CORS_ORIGINS` env var
- Vertex AI support for Google models via `USE_VERTEX_AI` + `GCP_PROJECT`

## Setup

### 1. Install Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for Python package management.

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...

# Optional
SEARCH_API_KEY=...          # SerpAPI or Brave key for web search tool
DATABASE_URL=postgres://...  # Use Postgres instead of JSON files
USE_VERTEX_AI=true           # Use Vertex AI for Google models
GCP_PROJECT=my-project       # GCP project for Vertex AI
```

You can provide keys for any subset of providers. Models from providers without a configured key will be skipped gracefully.

### 3. Run

**Option 1: Use the start script**
```bash
./start.sh
```

**Option 2: Run manually**

Terminal 1 (Backend on port 8001):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend on port 5173):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173.

## Architecture

```
frontend/          React + Vite SPA
  src/
    App.jsx        State management, SSE streaming handler
    api.js         API client (REST + SSE)
    components/
      ChatInterface.jsx   Main chat UI with all input controls
      ModelSelector.jsx   Provider-grouped model checkboxes + chairman dropdown
      TemplateSelector.jsx  System prompt template dropdown + config fields
      FileUpload.jsx       Drag & drop file upload
      ToolSelector.jsx     Tool toggle checkboxes
      ConnectorPanel.jsx   Connector toggle + config forms
      Stage1.jsx           Individual responses (tabs) + tool calls
      Stage2.jsx           Peer rankings + aggregate scores
      Stage3.jsx           Chairman synthesis
      Stage4.jsx           Self-reflection + re-run controls
      CostSummary.jsx      Cost breakdown display
      PromptingTips.jsx    Collapsible best practices

backend/           FastAPI (Python 3.10+)
  main.py          API endpoints + SSE streaming
  config.py        Models, pricing, env vars
  providers.py     OpenAI/Anthropic/Google SDK clients, multimodal, tool-use loops
  council.py       4-stage orchestration logic
  storage.py       Dual-mode storage (JSON / Postgres)
  db.py            asyncpg connection pool
  templates.py     System prompt templates
  files.py         File upload, storage, text extraction
  schema.sql       Postgres schema
  tools/           Tool-use framework
    registry.py    Tool registration + execution
    builtin.py     web_search, url_fetch, calculator, code_execution
  connectors/      External data connectors
    registry.py    Connector registration + execution
    builtin.py     web_search_prequery, url_content, rest_api
    oauth.py       OAuth token storage scaffolding
```

## Tech Stack

- **Backend**: FastAPI, official OpenAI/Anthropic/Google GenAI SDKs, asyncpg
- **Frontend**: React 18, Vite, react-markdown
- **Extraction**: pypdf, python-docx, openpyxl
- **Networking**: aiohttp, beautifulsoup4
- **Package Management**: uv (Python), npm (JavaScript)

## Credits

Originally inspired by [Andrej Karpathy's LLM Council concept](https://x.com/karpathy/status/1990577951671509438) for evaluating multiple LLMs side by side. Extended with file uploads, tool-use, connectors, cost tracking, self-reflection, and iterative re-run capabilities.
