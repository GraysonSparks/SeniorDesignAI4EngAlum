"""Shared settings for the AI4EngAlum RAG prototype. Override any of these with env vars."""

import os
from pathlib import Path

RAG_DIR = Path(__file__).resolve().parent
PROJECT_DIR = RAG_DIR.parent  # 3_Code/: rag/, content/, scraped_pages/, scraper/

# The hand-curated Q&A doc (content/). Both the .docx and .odt copies exist; content.py uses
# whichever was saved most recently unless CONTENT_DOC points at a specific file.
CONTENT_DOC = os.environ.get("CONTENT_DOC")
CONTENT_DOC_CANDIDATES = [
    PROJECT_DIR / "content" / "AI4EngAlum Giving Content for RAG.odt",
    PROJECT_DIR / "content" / "AI4EngAlum Giving Content for RAG.docx",
]
SCRAPED_DIR = Path(os.environ.get("SCRAPED_DIR", PROJECT_DIR / "scraped_pages"))

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "qwen3.5:9b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

CHROMA_DIR = Path(os.environ.get("CHROMA_DIR", RAG_DIR / "chroma_db"))
COLLECTION = "giving"

TOP_K = int(os.environ.get("TOP_K", "4"))
# How many earlier messages (user + assistant) from the live conversation are used per request.
# The client sends them with each request; the server never stores them.
HISTORY_MESSAGES = int(os.environ.get("HISTORY_MESSAGES", "6"))
# Cosine distance (0 = identical). Chunks farther than this are treated as "not relevant";
# if nothing is closer, the bot returns the fallback without calling the chat model.
MAX_DISTANCE = float(os.environ.get("MAX_DISTANCE", "0.5"))

FALLBACK_EMAIL = "augiving@auburn.edu"
FALLBACK_PHONE = "334-844-1427"
FALLBACK_CONTACT = f"the Auburn Engineering giving office at {FALLBACK_EMAIL} or {FALLBACK_PHONE}"
FALLBACK_REPLY = (
    "I don't have approved information to answer that. For help, please contact "
    f"{FALLBACK_CONTACT}."
)
