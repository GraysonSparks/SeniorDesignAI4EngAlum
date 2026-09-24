"""FastAPI backend for the giving chat widget.

    uvicorn app:app --port 8000

Then open http://localhost:8000/ for the test site (static/site/), or POST {"message": "..."} to /chat.
"""

import os
from typing import Literal

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import config
from rag import Assistant

app = FastAPI(title="AI4EngAlum Giving Assistant")

# The test site is served from this app (same origin), so CORS only matters when chat-widget.js
# is embedded on a page hosted somewhere else. Set CORS_ORIGINS="https://a.example,https://b.example" to allow those.
origins = [o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins,
                       allow_methods=["POST"], allow_headers=["Content-Type"])

assistant = Assistant()


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    # Earlier turns of the live conversation, sent by the widget with each request. They are used
    # to answer this one request and then discarded: nothing here is stored or logged.
    history: list[Turn] = Field(default_factory=list, max_length=20)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    fallback: bool


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, response: Response):
    response.headers["Cache-Control"] = "no-store"  # conversations aren't cached anywhere
    try:
        result = assistant.answer(req.message.strip(),
                                  [t.model_dump() for t in req.history])
    except Exception as e:  # Ollama down, collection missing, etc.
        raise HTTPException(status_code=503, detail=f"Assistant unavailable: {e}")
    return ChatResponse(answer=result["answer"], sources=result["sources"],
                        fallback=result["fallback"])


@app.post("/reload-rules")
def reload_rules():
    """Pick up edits to the Response Rules in the content doc without restarting."""
    assistant.reload_rules()
    return {"rules_source": assistant.rules_source}


@app.get("/health")
def health():
    return {"chunks": assistant.collection.count(), "chat_model": config.CHAT_MODEL,
            "embed_model": config.EMBED_MODEL, "rules_source": assistant.rules_source}


# Mounted last so the API routes above take precedence. Serves the test site and chat-widget.js.
app.mount("/", StaticFiles(directory=config.RAG_DIR / "static" / "site", html=True), name="site")
