# MediGuide — complete beginner's project plan

A health-information agentic AI system (triage agent + retrieval agent + safety agent) built solo, for practice, before your real group assignment. This guide assumes you know basic Python but nothing about LLM agents, RAG, or MCP yet — every new concept is explained before you're asked to use it.

**Scope reminder:** MediGuide gives general health information and tells people when to see a professional. It never diagnoses. Keep this sentence in your head — it shapes almost every design decision below.

---

## Project status (update this as you go)

Keep this section current — it's what lets you (or a new chat) pick up exactly where you left off without re-explaining everything.

**Key decisions locked in:**
- Domain: health-information assistant, explicitly *not* diagnostic
- LLM: Gemini, via the `google-genai` package (`from google import genai`) — switched from Anthropic to avoid separate API billing
- Current working model name: `gemini-3.5-flash` (verify at aistudio.google.com if this 404s later — Google's model names change often)
- OS: Windows, using Git Bash (MINGW64)

**Progress so far:**
- [x] Venv created and activated correctly (`source venv/Scripts/activate` in Git Bash)
- [x] All packages installed inside the venv: `google-genai`, `mcp`, `chromadb`, `spacy` (+ `en_core_web_sm`), `fastapi`, `uvicorn`, `pyjwt`, `passlib`, `cryptography`, `python-multipart`
- [x] Part 2 sanity check passing — `test_api.py` gets a real response from Gemini
- [x] Week 2 — retrieval agent ingestion: 5 sample health docs (migraine, common cold/flu, type 2 diabetes, asthma, seasonal allergies) in `data/sources/`; `agents/retrieval_agent/ingest.py` chunks each doc along its `## ` section headers (not raw word count — keeps chunks topically coherent) and stores them in a local Chroma collection; `agents/retrieval_agent/query.py` takes a plain-text question and returns top-3 chunks. Uses Chroma's built-in local embedding function (no API key needed for this step).
- [ ] Week 3 — retrieval agent as MCP server
- [ ] Week 4 — safety agent
- [ ] Week 5 — triage agent / MCP host
- [ ] Week 6 — security layer + UI
- [ ] Week 7 — Responsible AI pass
- [ ] Week 8 — report, video, repo, viva prep

**Next step:** Week 3 — add a spaCy NER pass to refine the retrieval query, then wrap `search_health_info` as an MCP server.

**Resuming in a new chat:** upload this file at the start of the conversation and say which week you're working on (e.g. "I'm starting Week 2, help me write the ingestion script"). No need to re-explain the architecture or tech stack — it's all here.

---

## How to use this guide

Work through the parts in order. Don't skip Part 1 even if you're impatient to code — the concepts (RAG, NER, MCP) are used constantly from Week 2 onward, and five minutes of reading now saves hours of confusion later. Each week in Part 3 has a **Learn / Build / Done when** structure — "Done when" is your checkpoint before moving on.

---

## Part 0 — Before you start

1. Install Python 3.10+ and confirm with `python3 --version`.
2. Get a Gemini API key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) — free tier, no credit card required, and it's separate from any Google Cloud billing.
3. Install a code editor (VS Code is fine) with the Python extension.
4. Create a GitHub account and repo now (empty is fine) — you'll commit as you go, not all at the end.
5. Create your project folder and a virtual environment:

```bash
mkdir mediguide && cd mediguide
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install google-genai mcp chromadb spacy fastapi uvicorn pyjwt passlib cryptography python-multipart
python -m spacy download en_core_web_sm
```

If any install fails, it's almost always a Python version mismatch — check `python3 --version` first.

---

## Part 1 — Core concepts crash course

Read each of these once, in order. They build on each other.

**Agent.** In this project, an "agent" is just a program that (a) can call an LLM to reason, and (b) can call tools to take action, rather than only outputting text. A single Gemini API call that returns an answer is not an agent. A program that decides *which tool to call* based on the query, calls it, and uses the result — that's an agent.

**RAG (retrieval-augmented generation).** LLMs don't know your specific documents. RAG means: search your own documents for the relevant chunk, then hand that chunk to the LLM as context before it answers. This is how your retrieval agent avoids making things up — it only answers from what it actually retrieved.

**Embeddings & vector databases.** To "search" documents by meaning (not just keyword match), you convert text into a list of numbers (an embedding) that captures its meaning, and store these in a vector database. A query gets embedded the same way, and the database returns the stored chunks whose embeddings are numerically closest. Chroma (`chromadb`) does this locally with almost no setup — good for a beginner.

**NER (named entity recognition).** An NLP technique that pulls structured entities out of free text — e.g., turning "I've had a bad headache and fever since yesterday" into `{symptom: headache, symptom: fever, duration: since yesterday}`. spaCy does general-purpose NER out of the box; for this project you'll mostly use it to tag symptom/condition-like terms so your retrieval query is more precise than the raw sentence.

**MCP (Model Context Protocol).** A standard way for an LLM-driven program (the "host") to call tools exposed by separate "servers," over a defined protocol instead of ad-hoc function calls. In MediGuide: the triage agent is the **host**, and the retrieval agent and safety agent are each an **MCP server** exposing one or two tools (e.g. `search_health_info`, `check_safety`). This is the "agent communication protocol" your rubric explicitly asks about — official docs: [modelcontextprotocol.io](https://modelcontextprotocol.io).

**API security basics.**
- *Authentication* — proving who's calling your API. JWT (JSON Web Tokens) is a common, beginner-friendly approach: a user logs in once, gets a signed token, and sends it with every request.
- *Input sanitization* — never trust raw user text going straight into a prompt or a database query. At minimum: strip/escape unexpected characters, cap input length, and reject obvious prompt-injection patterns ("ignore previous instructions" etc.).
- *Encryption at rest* — if you store any user data, encrypt it on disk (the `cryptography` package's Fernet recipe is a one-line beginner-friendly option), don't store it in plain text.

---

## Part 2 — Environment sanity check

Before building anything agent-related, confirm the basics work in isolation.

```python
# test_api.py
from google import genai

client = genai.Client()  # reads GEMINI_API_KEY from env
response = client.models.generate_content(
    model="gemini-3.5-flash",  # check aistudio.google.com if this ever 404s — Google's lineup changes often
    contents="Say hello in one sentence."
)
print(response.text)
```

Set your key first: `export GEMINI_API_KEY=...` (Windows: `set` or add to `.env`). **Done when:** this script prints a real response.

Note the package name: `google-genai` is what you `pip install`, but you `import` it as `from google import genai` — mismatched names are common in Google's Python libraries, this isn't a typo.

---

## Part 3 — Week-by-week build plan

### Week 1 — Setup + first working script
- **Learn:** how the `google-genai` SDK works; how `.env` files keep secrets out of git.
- **Build:** the sanity check above, plus a `.gitignore` (exclude `venv/`, `.env`) and your first commit.
- **Done when:** repo exists on GitHub with a working "hello Gemini" script and a `.env.example` (no real keys committed).

### Week 2 — Retrieval agent, part 1: ingestion
- **Learn:** how chunking works (splitting long documents into ~200-500 word pieces so embeddings stay meaningful); Chroma basics.
- **Build:** gather 3-5 public health reference documents (e.g. condition overview pages from a source like the NHS or WHO — plain text or markdown is easiest to start with). Write a script that chunks them and stores them in a local Chroma collection.
- **Done when:** you can run a script that takes a plain-text query like "what causes migraines" and returns the 3 most relevant chunks.

### Week 3 — Retrieval agent, part 2: NER + wrap as MCP server
- **Learn:** spaCy's `nlp(text).ents`; MCP server basics (a server exposes named tools with typed inputs/outputs).
- **Build:** add a spaCy pass that extracts symptom/condition-like entities from the query and uses them to refine the search. Wrap the whole thing as an MCP server exposing one tool: `search_health_info(query: str) -> list[chunk]`.
- **Done when:** you can start the MCP server standalone and call `search_health_info` from a small test client script.

### Week 4 — Safety agent
- **Learn:** nothing new technically — this is mostly design work. The hard part is deciding what counts as a red flag.
- **Build:** a `red_flags.json` file listing emergency symptom keywords/phrases (chest pain, difficulty breathing, suicidal thoughts, severe bleeding, etc.) with a short explanation for each. Wrap a `check_safety(query: str) -> {escalate: bool, reason: str}` tool as a second MCP server.
- **Done when:** the tool correctly flags a test set of 5 "obviously urgent" queries and correctly does *not* flag 5 "obviously routine" queries.

### Week 5 — Triage agent (the MCP host)
- **Learn:** MCP client/host basics — connecting to multiple servers and letting Gemini decide which tool to call (Gemini calls this function calling; it also has experimental built-in support for calling local MCP servers directly, which can simplify this step — worth checking the docs before hand-rolling the routing logic).
- **Build:** the orchestrator. Logic order matters: **always** call `check_safety` first; only call `search_health_info` and compose an answer if no red flag was raised; if a red flag was raised, return the escalation message instead of a normal answer.
- **Done when:** you can run one script that takes a raw user question and returns either (a) a cited health-information answer or (b) an escalation message — correctly, for both cases.

### Week 6 — Security layer (your informal "mid-evaluation" milestone)
- **Learn:** FastAPI basics; JWT issuing/verifying with `pyjwt`; Fernet encryption.
- **Build:** wrap the triage agent in a FastAPI app with a login endpoint (issues a JWT) and a protected `/ask` endpoint (requires the JWT). Sanitize all incoming text before it reaches the LLM. If you store any session/history data, encrypt it before writing to disk.
- **Done when:** an unauthenticated request to `/ask` is rejected, and an authenticated one works end to end through triage → safety → retrieval.
- **This is a good point to pause and mentally "present" your progress** — architecture, agent roles, working demo, brief Responsible AI notes, brief commercialization idea — exactly what a mid-evaluation asks for.

### Week 7 — Responsible AI pass
- **Learn:** nothing new — this is testing and writing, not coding.
- **Build:** (1) a first-use disclaimer shown to the user stating the system gives general information only; (2) a small fairness test set — the same 3-4 symptoms phrased formally, informally, and in simplified/non-native English — and check retrieval quality stays consistent across phrasings; (3) make sure every answer cites which source chunk it came from.
- **Done when:** you have a short written note (half a page) covering fairness, transparency, and privacy decisions you actually made, with evidence (test results, code references) for each.

### Week 8 — Report, video, repo, mock viva
- **Build:** write the report using whatever structure your real module template uses (system design, methodology, Responsible AI, commercialization, evaluation); record a 3-5 minute screen demo showing a normal query answered with citations *and* a red-flag query triggering escalation; clean up the GitHub repo with a proper README (setup steps, usage, architecture summary); write out answers to the viva-style questions in Part 4 below and say them out loud once.
- **Done when:** a stranger could clone your repo, follow the README, and get the demo running.

---

## Part 3.5 — How the user actually interacts with it

Everything above is backend: agents talking to each other, an API endpoint. Something still needs to sit in front of it for a real person to type into. Three options, in order of effort:

1. **A CLI test script** (fastest, no UI code at all) — a loop that reads input from the terminal and prints the response. Fine for your own testing during Weeks 1-5, but looks bare for a demo video and doesn't showcase the product feel.
2. **Streamlit** (recommended) — a small Python library that turns a script into a simple web page with almost no frontend code. Enough to build a chat-style interface in under an hour, and it looks like a real product on screen recording.
3. **A custom web frontend** (React/HTML+JS) — only worth it if you specifically want polish for the commercialization pitch. More work, and not something the rubric requires — the marks are in the agents, protocols, NLP, IR, and security, not the UI framework.

For a solo practice project, go with Streamlit. Minimal example, once your `/ask` endpoint exists:

```python
# ui/app.py
import streamlit as st
import requests

st.title("MediGuide")
st.caption("General health information only — not a diagnosis. In an emergency, contact local emergency services.")

query = st.text_input("Ask a health question")
if query:
    resp = requests.post(
        "http://localhost:8000/ask",
        json={"query": query},
        headers={"Authorization": f"Bearer {st.session_state.get('token', '')}"}
    )
    st.write(resp.json())
```

Run it with `streamlit run ui/app.py` alongside your FastAPI server. Build this in Week 6 once the security layer exists (so the UI can exercise the real login → ask flow), and it becomes the thing you actually screen-record for your demo and video in Week 8.

---

## Part 4 — Mapping your work to the rubric

| Rubric asks for | What proves it in MediGuide |
|---|---|
| System architecture, scalability, Responsible AI | The architecture diagram + a paragraph on how each agent could scale independently (e.g. retrieval agent behind a queue if load grows) |
| Agent roles & communication flow | Triage agent as MCP host, retrieval + safety agents as MCP servers — name this explicitly, don't just say "agents talk to each other" |
| Progress demo / demonstration of system | The Week 6 and Week 8 recordings: normal query + red-flag query |
| Responsible AI check | Your Week 7 write-up: fairness test results, citation behavior, disclaimer, privacy handling |
| Commercialization pitch | B2B licensing to clinics/telehealth platforms — see below |
| NLP technique | spaCy NER on symptoms/conditions |
| Information retrieval | Chroma + chunking + RAG |
| Security features | JWT auth, input sanitization, Fernet encryption |
| Communication protocol | MCP, explained with the host/server roles above |

**Commercialization pitch (practice version):** B2B licensing to clinics, telehealth platforms, or corporate wellness programs, priced per-seat or per-month per clinic; target users are healthcare providers who want a pre-consultation triage layer, not direct-to-consumer, since liability and trust are easier to manage with a provider as the customer.

**Viva-prep questions to have real answers for:**
- Why MCP instead of just calling functions directly?
- Walk me through what happens, step by step, when a user asks something with a red-flag symptom.
- What's one fairness issue you tested for, and what did you find?
- What data do you store, and how is it protected?
- If you had to add a fourth agent, what would it do?

---

## Part 5 — Suggested repo structure

```
mediguide/
├── README.md
├── .env.example
├── requirements.txt
├── agents/
│   ├── retrieval_agent/      # MCP server: search_health_info
│   ├── safety_agent/         # MCP server: check_safety
│   └── triage_agent/         # MCP host + orchestration logic
├── api/
│   └── main.py               # FastAPI app: auth, /ask endpoint
├── ui/
│   └── app.py                # Streamlit chat interface
├── data/
│   ├── sources/               # raw reference documents
│   └── red_flags.json
├── tests/
│   └── fairness_test_set.py
└── docs/
    ├── architecture.md
    └── responsible_ai_notes.md
```

---

## Part 6 — Common beginner pitfalls

- **Building the triage agent first.** Build retrieval and safety as standalone, independently testable pieces first — debugging three new concepts (MCP, RAG, orchestration) at once is much harder than debugging them one at a time.
- **Skipping the "does no answer" test.** It's easy to test that your system answers well; it's easy to forget to test that it correctly *refuses* to answer (red-flag case) or correctly says "I don't have information on that" rather than guessing.
- **Committing your API key.** Always use `.env` + `.gitignore`, never hardcode keys in a script you might commit.
- **Over-scoping the knowledge base.** 3-5 well-chosen documents you understand well beat 50 scraped pages you haven't read — you need to be able to explain retrieval quality in the viva.

---

## Part 7 — Reference links

- Gemini API docs: [ai.google.dev/gemini-api/docs](https://ai.google.dev/gemini-api/docs)
- Model Context Protocol: [modelcontextprotocol.io](https://modelcontextprotocol.io)
- spaCy (NER): [spacy.io/usage/linguistic-features#named-entities](https://spacy.io/usage/linguistic-features#named-entities)
- Chroma (vector DB): [docs.trychroma.com](https://docs.trychroma.com)
- FastAPI: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- PyJWT: [pyjwt.readthedocs.io](https://pyjwt.readthedocs.io)
- `cryptography` Fernet recipe: [cryptography.io/en/latest/fernet](https://cryptography.io/en/latest/fernet)
