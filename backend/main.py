"""FastAPI backend for LLM Council."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from . import storage
from .config import AVAILABLE_MODELS, DATABASE_URL, MODEL_PRICING
from .templates import SYSTEM_PROMPT_TEMPLATES
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, stage4_self_reflection, calculate_aggregate_rankings
from .providers import query_model
from . import files as file_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB pool if Postgres is configured
    if DATABASE_URL:
        from .db import get_pool, close_pool
        await get_pool()
    yield
    # Shutdown: close DB pool
    if DATABASE_URL:
        from .db import close_pool
        await close_pool()


app = FastAPI(title="LLM Council API", lifespan=lifespan)

# Configurable CORS origins
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    council_models: List[str]
    chairman_model: str
    system_prompt: Optional[str] = None
    previous_iteration: Optional[Dict[str, Any]] = None
    provide_context_to_council: bool = False
    enabled_tools: Optional[List[str]] = None
    enabled_connectors: Optional[List[Dict[str, Any]]] = None


class OptimizePromptRequest(BaseModel):
    """Request to optimize a prompt."""
    prompt: str
    model: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/models")
async def get_models():
    """Return available models organized by provider."""
    return AVAILABLE_MODELS


@app.get("/api/pricing")
async def get_pricing():
    """Return model pricing (per 1M tokens)."""
    return {
        model: {"input": inp, "output": out}
        for model, (inp, out) in MODEL_PRICING.items()
    }


@app.get("/api/templates")
async def get_templates():
    """Return available system prompt templates."""
    return SYSTEM_PROMPT_TEMPLATES


@app.get("/api/tools")
async def get_tools():
    """Return available tools for Stage 1 tool-use."""
    from .tools.registry import TOOL_REGISTRY
    return [
        {"name": t.name, "description": t.description}
        for t in TOOL_REGISTRY.values()
    ]


@app.get("/api/connectors")
async def get_connectors():
    """Return available external connectors."""
    from .connectors.registry import CONNECTOR_REGISTRY
    return [
        {
            "name": c.name,
            "description": c.description,
            "type": c.connector_type,
            "config_schema": c.config_schema,
        }
        for c in CONNECTOR_REGISTRY.values()
    ]


# --- File upload endpoints ---

@app.post("/api/conversations/{conversation_id}/files")
async def upload_files(conversation_id: str, files: List[UploadFile] = File(...)):
    """Upload files to a conversation."""
    conversation = await storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    results = []
    for f in files:
        data = await f.read()
        cf = await file_manager.save_file(
            conversation_id, f.filename, f.content_type or "application/octet-stream", data
        )
        results.append({
            "id": cf.id,
            "filename": cf.filename,
            "content_type": cf.content_type,
            "size_bytes": cf.size_bytes,
            "is_image": cf.is_image,
            "created_at": cf.created_at,
        })
    return results


@app.get("/api/conversations/{conversation_id}/files")
async def list_files(conversation_id: str):
    """List files attached to a conversation."""
    return await file_manager.get_conversation_files(conversation_id)


@app.delete("/api/conversations/{conversation_id}/files/{file_id}")
async def delete_file(conversation_id: str, file_id: str):
    """Delete a file from a conversation."""
    deleted = await file_manager.delete_file(conversation_id, file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    return {"ok": True}


@app.get("/api/conversations/{conversation_id}/files/{file_id}")
async def download_file(conversation_id: str, file_id: str):
    """Download a file."""
    path = await file_manager.get_file_path(conversation_id, file_id)
    if path is None:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return await storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = await storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = await storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = await storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    await storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        await storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content,
        request.council_models,
        request.chairman_model,
        request.system_prompt,
    )

    # Add assistant message with all stages
    await storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = await storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            await storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Build the query for council models (may include context for re-runs)
            council_query = request.content
            if request.previous_iteration and request.provide_context_to_council:
                context_note = (
                    f"[CONTEXT FROM PREVIOUS ANALYSIS]\n"
                    f"This is a re-analysis. The previous query was: \"{request.previous_iteration.get('query', '')}\"\n"
                    f"The chairman's critique of the previous analysis: {request.previous_iteration.get('critique', 'N/A')}\n"
                    f"[END CONTEXT]\n\n"
                    f"{request.content}"
                )
                council_query = context_note

            # Fetch file context for this conversation
            file_context, image_attachments = await file_manager.get_file_content_for_context(
                conversation_id
            )

            # Run connectors to inject additional context
            connector_context = ""
            if request.enabled_connectors:
                from .connectors.registry import run_connector
                for conn_cfg in request.enabled_connectors:
                    try:
                        result = await run_connector(conn_cfg.get("name", ""), conn_cfg.get("config", {}))
                        if result:
                            tag = conn_cfg["name"].upper().replace(" ", "_")
                            connector_context += f"[{tag} DATA]\n{result}\n[END {tag} DATA]\n\n"
                    except Exception as e:
                        print(f"Connector {conn_cfg.get('name')} failed: {e}")

            # Merge connector context into file context
            if connector_context:
                file_context = connector_context + (file_context or "")

            # Resolve enabled tools
            tool_defs = None
            if request.enabled_tools:
                from .tools.registry import get_enabled_tools
                tool_defs = get_enabled_tools(request.enabled_tools)

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(
                council_query,
                request.council_models,
                request.system_prompt,
                file_context=file_context or None,
                image_attachments=image_attachments or None,
                tools=tool_defs,
            )
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(
                request.content, stage1_results, request.council_models
            )
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(
                request.content, stage1_results, stage2_results, request.chairman_model,
                previous_iteration=request.previous_iteration,
            )
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Stage 4: Chairman self-reflection
            yield f"data: {json.dumps({'type': 'stage4_start'})}\n\n"
            stage4_result = await stage4_self_reflection(
                user_query=request.content,
                system_prompt=request.system_prompt,
                stage1_results=stage1_results,
                stage3_result=stage3_result,
                chairman_model=request.chairman_model,
                previous_iteration=request.previous_iteration,
            )
            yield f"data: {json.dumps({'type': 'stage4_complete', 'data': stage4_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                await storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Calculate total cost summary
            stage1_cost = sum(r.get("cost", 0) for r in stage1_results)
            stage2_cost = sum(r.get("cost", 0) for r in stage2_results)
            stage3_cost = stage3_result.get("cost", 0)
            stage4_cost = stage4_result.get("cost", 0)
            total_cost = stage1_cost + stage2_cost + stage3_cost + stage4_cost

            # Build per-model breakdown
            model_costs = {}
            for r in stage1_results + stage2_results:
                m = r["model"]
                model_costs[m] = model_costs.get(m, 0) + r.get("cost", 0)
            model_costs[request.chairman_model] = model_costs.get(request.chairman_model, 0) + stage3_cost + stage4_cost

            cost_summary = {
                "stage1": round(stage1_cost, 6),
                "stage2": round(stage2_cost, 6),
                "stage3": round(stage3_cost, 6),
                "stage4": round(stage4_cost, 6),
                "total": round(total_cost, 6),
                "by_model": {m: round(c, 6) for m, c in model_costs.items()},
            }
            yield f"data: {json.dumps({'type': 'cost_summary', 'data': cost_summary})}\n\n"

            # Save complete assistant message
            await storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result,
                stage4=stage4_result,
                run_config={
                    "system_prompt": request.system_prompt,
                    "council_models": request.council_models,
                    "chairman_model": request.chairman_model,
                },
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/optimize-prompt")
async def optimize_prompt(request: OptimizePromptRequest):
    """Optimize a user's prompt using a selected model."""
    system_prompt = """You are a prompt engineering expert. Your task is to improve the user's prompt to get better responses from an LLM council.

Rewrite the prompt to be:
- More specific and clear
- Well-structured with context
- Explicit about desired format and depth
- Free of ambiguity

Return ONLY the improved prompt text, nothing else. Do not add preamble like "Here's the improved prompt:" — just output the prompt itself."""

    messages = [{"role": "user", "content": request.prompt}]
    response = await query_model(request.model, messages, system_prompt=system_prompt)

    if response is None:
        raise HTTPException(status_code=500, detail="Failed to optimize prompt")

    return {"optimized_prompt": response["content"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
