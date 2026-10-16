# AI4EngAlum RAG backend

Local RAG chat assistant for eng.auburn.edu/giving: Ollama `qwen3.5:9b` for answers (thinking off),
`nomic-embed-text` for embeddings, embedded ChromaDB for the index, FastAPI for `/chat`.

## Setup (once)

```bash
ollama pull qwen3.5:9b
ollama pull nomic-embed-text
uv venv --python 3.12 ~/.local/share/venvs/ai4engalum-rag   # kept outside Dropbox
VIRTUAL_ENV=~/.local/share/venvs/ai4engalum-rag uv pip install -r requirements.txt
source ~/.local/share/venvs/ai4engalum-rag/bin/activate
```

## Run

```bash
python ingest.py                 # rebuild the index; re-run after editing the doc or scraped pages
uvicorn app:app --port 8000      # test site + chat at http://localhost:8000/
python run_test_prompts.py       # runs the doc's "Suggested Initial Test Prompts"
python content.py                # print every chunk exactly as it will be embedded (reads ../content/)
python eval_models.py qwen3.5:9b gemma4:12b   # scored comparison of chat models (56 cases)
python routing.py                # print the staff routing table built from the directory
python test_contact.py           # checks the follow-up form endpoint (10 checks)
```

`POST /reload-rules` picks up edits to the doc's Response Rules without restarting the server
(chunk edits need `python ingest.py` + a restart).

## What gets indexed (55 chunks)

| Source | Chunks | Notes |
|---|---|---|
| `AI4EngAlum Giving Content for RAG` (.odt or .docx, whichever was saved last) | 16 | One per `GIVING-XXX-01` section. Question + answer embedded; `Source:` URLs stored as metadata. |
| Same doc, "Example Questions and Grounded Answers" | 15 | One per numbered Q&A. Examples that only describe bot behavior ("The chatbot should...") are skipped; the response rules cover them. An example without its own URL takes the source of the curated chunk it overlaps with most (run `python content.py` to see the matches). |
| Staff directory (`scraped_pages/eng_auburn_edu_admin_development_index_html.txt`) | 14 | One per person, role description first. |
| Department campaign pages (`scraped_pages/give_auburn_edu_campaigns_*.txt`) | 10 | Only the department-specific paragraphs; shared boilerplate dropped. The department's advancement liaison (parsed from the directory) is appended. |

The doc's **Recommended Response Rules** become the core of the system prompt. `rag.py` adds
fixed instructions for grounding, the tax/legal refusal, prompt-injection handling, and the fallback contact
(augiving@auburn.edu / 334-844-1427).

## Guardrails outside the prompt

- If no chunk is within cosine distance `MAX_DISTANCE` (0.5), the fixed fallback reply is returned without calling the model.
- Any URL in the answer that isn't one of the retrieved chunks' sources is replaced with the best source URL.
- Cited `sources` include only chunks within 0.08 of the best match.

Settings (models, top-k, threshold, paths) live in `config.py` and can be overridden with env vars.

## Staff routing (Story 9)

Retrieval finds the right person when a question uses the directory's wording, but it missed
questions such as "I live in Atlanta, who can I meet with?" or "who helps a student org with
fundraising?". `routing.py` adds a table of 30 routes (9 department liaisons, 12 programs, 9 regions)
that is matched against any question asking for a person:

- The table holds topics and the phrase that identifies the owner in the staff directory, never a
  name, email, or phone number. Contact details come from `scraped_pages/` at startup, so
  re-scraping the directory updates the routes. `python routing.py` flags a route whose phrase no
  longer matches anyone.
- A matched contact is placed first in the model's context. If the model still declines, the backend
  states the contact itself, so a routed question never ends in a bare decline.
- `/chat` returns the routed staff in `contacts`, and the widget shows each as a card with their
  email, phone, and an "Ask <name> to contact me" button.
- Materials Engineering has no liaison in the directory, so it has no route and no card.

## Follow-up requests (Story 11)

A visitor can leave their details for a staff member to follow up:

- **When the form appears:** from the button on a contact card, or when the visitor asks to be
  contacted ("can someone call me?"). That request gets a fixed reply with `offer_contact: true`
  and no model call.
- **What is collected:** first name, last name, email, optional phone, optional message, and the
  routed staff member if there is one. The consent box must be ticked; `POST /contact` rejects a
  request without it.
- **Where it goes:** one line per request in `rag/data/contact_requests.jsonl` (gitignored; override
  with `CONTACT_REQUESTS_FILE`). The conversation, IP address, and browser details are not stored.
  All writes go through `leads.save_request()`, the one place to change when Advancement decides
  where requests should live.
- **Not built yet:** notifying staff of a new request (Story 10), which needs a delivery channel
  on the hosting side, and spam protection (rate limiting or a CAPTCHA) before this is public.

## Test site (`static/site/`)

A local mock of the eng.auburn.edu/giving pages for testing the assistant in context: giving home,
Ways to Give, EAGLE Society, and the staff directory. It uses the live site's colors and text, and all
Give/Visit buttons link to the real Auburn pages. A banner marks it as a Team 21 test mock, so keep it
local and don't host it publicly.

The chat is a single drop-in file, `chat-widget.js`, loaded with
`<script src="chat-widget.js" defer></script>`. It posts to `/chat` on whatever server it was loaded
from (override with `data-endpoint="..."`). Its CSS is scoped under `#aug-chat`, and the conversation
persists across pages for the browser session. To embed it on a page served from another origin,
start the backend with `CORS_ORIGINS=<that origin>`.

## Conversation memory (live only)

The assistant follows up within a conversation ("Who is the liaison for *that* department?"), but
nothing about the conversation is stored. (The follow-up form above is separate: it stores only
what the visitor submits in it.)

- **Browser:** the widget keeps the conversation in page memory only. Nothing goes to localStorage,
  sessionStorage, or cookies. The one exception is a yes/no "pop-up dismissed" flag in sessionStorage,
  which holds no conversation content. A reload, page change, tab close, or **Clear** ends the conversation.
- **Server:** each `/chat` request carries the last 6 messages (`HISTORY_MESSAGES` in `config.py`).
  The server uses them for that one answer and discards them. Conversations go to no database, no
  file, and no logging of message text (uvicorn's access log records only `POST /chat` and the status code).
  Responses are sent with `Cache-Control: no-store`.
- **Follow-ups:** when there's history, the model first rewrites the latest message as a standalone
  question for the search ("that department" → "the Computer Science and Software Engineering
  Department"). The answer step sees both the visitor's wording and the resolved question.
- **Ollama** keeps the most recent prompt in GPU memory while the model is loaded (default 5 minutes
  after the last request) to speed up the next one. That memory is overwritten by later requests and
  never written to disk.

`eval_models.py` includes 7 multi-turn cases: follow-ups, a topic switch, and an injection attempt
inside a follow-up.
