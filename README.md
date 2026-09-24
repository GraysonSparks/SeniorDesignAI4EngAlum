# AI4EngAlum — Auburn Engineering Giving Assistant (Team 21)

A local RAG chat assistant for eng.auburn.edu/giving. Setup, running, testing, and design notes are in
[`rag/README.md`](rag/README.md).

- `rag/`: FastAPI backend, ingestion, evaluation, and a test website with the drop-in chat widget
- `content/`: hand-curated giving Q&A doc (the primary knowledge source)
- `scraped_pages/`: cleaned text of the official giving pages (staff directory, department pages)
- `scraper/`: the script that produced `scraped_pages/`
