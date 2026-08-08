# MediGuide 🩺

> A multi-agent AI health information assistant that answers general health questions, retrieves evidence from trusted documents, and automatically escalates emergencies — built with LLMs, RAG, NLP, and MCP.

**Important:** MediGuide provides general health information only. It is not a diagnostic tool and does not replace professional medical advice. In an emergency, contact your local emergency services immediately.

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Agents](#agents)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Running the System](#running-the-system)
- [API Reference](#api-reference)
- [Responsible AI](#responsible-ai)
- [Commercialization](#commercialization)
- [Contributors](#contributors)

---

## Overview

MediGuide is a three-agent agentic AI system designed to answer general health questions using information retrieved from trusted health reference documents. Every query is first screened for emergency red flags before any retrieval or generation takes place. If an emergency is detected, the system escalates immediately with guidance to seek professional care — it does not attempt to answer.

The system was built as part of the IT3041 Information Retrieval and Web Analytics group assignment, demonstrating agentic behaviour, multi-agent communication via MCP, RAG-based information retrieval, NLP-driven query refinement, and responsible AI practices.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        User                             │
│              (Streamlit UI / API client)                │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP (JWT authenticated)
                        ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Layer                         │
│         POST /login   │   POST /ask                     │
│         JWT auth + input sanitization                   │
└───────────────────────┬─────────────────────────────────┘
                        │ function call
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Triage Agent  (MCP Host)                   │
│                                                         │
│  1. call check_safety()  ──────────────────────────┐   │
│  2. if escalate → return reason (stop)             │   │
│  3. call search_health_info()                      │   │
│  4. build RAG prompt + call Gemini                 │   │
│  5. return cited answer                            │   │
└──────────┬──────────────────────────┬──────────────┘   │
           │ MCP (stdio)              │ MCP (stdio)       │
           ▼                          ▼                   │
┌──────────────────┐      ┌──────────────────────────┐   │
│  Safety Agent    │      │    Retrieval Agent        │   │
│  (MCP Server)    │      │    (MCP Server)           │   │
│                  │      │                           │   │
│  check_safety()  │      │  search_health_info()     │   │
│  red_flags.json  │      │  spaCy NER → Chroma       │   │
│  keyword match   │      │  vector search → chunks   │   │
└──────────────────┘      └──────────────────────────┘
```

**Communication protocol:** All inter-agent communication uses the [Model Context Protocol (MCP)](https://modelcontextprotocol.io) over stdio transport. Each agent runs as an independent process and exposes typed tools. The triage agent acts as the MCP host; the safety and retrieval agents are MCP servers.

---

## Agents

### Safety Agent — `agents/safety_agent/`

Screens every incoming query for emergency red-flag keywords before any retrieval or generation occurs.

- **Tool exposed:** `check_safety(query: str) -> {escalate: bool, reason: str}`
- **Method:** case-insensitive keyword matching against `data/red_flags.json`
- **Red flag categories:** chest pain, breathing difficulty, suicidal ideation, severe bleeding, stroke signs, unconsciousness, anaphylaxis, overdose, seizure, high fever
- **Key design decision:** loaded at import time (not per-call) for performance; uses `.lower()` so capitalisation never causes a miss

### Retrieval Agent — `agents/retrieval_agent/`

Searches a local vector database of health reference documents and returns the most relevant chunks for a given query.

- **Tool exposed:** `search_health_info(query: str, k: int) -> list[chunk]`
- **NLP step:** spaCy EntityRuler with custom SYMPTOM/CONDITION labels extracts domain terms from the query and appends them before embedding — improves semantic match accuracy
- **Storage:** ChromaDB persistent vector store, chunked by document section headers (not fixed word count) to preserve topical coherence
- **Knowledge base:** 5 health reference documents — migraine, common cold/flu, type 2 diabetes, asthma, seasonal allergies

### Triage Agent — `agents/triage_agent/`

The MCP host and orchestrator. Enforces the safety-first logic order and composes the final answer.

- **Logic order:** safety check → (escalate or) retrieve → prompt Gemini → return cited answer
- **LLM:** Gemini (`gemini-3.5-flash`) via the `google-genai` SDK
- **RAG prompt:** instructs Gemini to answer only from retrieved context and cite the source of each point
- **Exposes:** `ask(query: str) -> {type, answer/message, sources}` — a synchronous wrapper used by the FastAPI layer

---

## Tech Stack

| Component           | Technology                                                |
| ------------------- | --------------------------------------------------------- |
| LLM                 | Google Gemini (`gemini-3.5-flash`) via `google-genai`     |
| Agent communication | Model Context Protocol (MCP) — `mcp` Python SDK / FastMCP |
| Vector database     | ChromaDB (local persistent store)                         |
| NLP / NER           | spaCy (`en_core_web_sm` + custom EntityRuler)             |
| Web framework       | FastAPI + Uvicorn                                         |
| Authentication      | JWT via `pyjwt`                                           |
| Encryption          | Fernet symmetric encryption via `cryptography`            |
| UI                  | Streamlit                                                 |
| Language            | Python 3.10+                                              |

---

## Project Structure

```
mediguide/
├── README.md
├── .env.example                  # environment variable template (no real keys)
├── requirements.txt
│
├── agents/
│   ├── retrieval_agent/          # MCP server — exposes search_health_info
│   │   ├── ingest.py             # chunk documents and store in Chroma
│   │   ├── query.py              # CLI: ask a question, see top-3 chunks
│   │   ├── ner.py                # spaCy EntityRuler + refine_query()
│   │   ├── retrieval.py          # shared search logic (NER → Chroma)
│   │   ├── server.py             # MCP server entry point
│   │   └── test_client.py        # MCP client smoke test
│   │
│   ├── safety_agent/             # MCP server — exposes check_safety
│   │   ├── __init__.py
│   │   ├── checker.py            # keyword matching logic
│   │   ├── server.py             # MCP server entry point
│   │   └── test_client.py        # MCP client smoke test
│   │
│   └── triage_agent/             # MCP host — orchestrates both servers
│       ├── __init__.py
│       ├── triage.py             # orchestration logic + Gemini call
│       └── test_triage.py        # end-to-end smoke test
│
├── api/
│   └── main.py                   # FastAPI app: /login and /ask endpoints
│
├── ui/
│   └── app.py                    # Streamlit chat interface
│
├── data/
│   ├── sources/                  # raw health reference documents (.md)
│   │   ├── migraine.md
│   │   ├── common_cold_and_flu.md
│   │   ├── type_2_diabetes.md
│   │   ├── asthma.md
│   │   └── seasonal_allergies.md
│   └── red_flags.json            # emergency keyword categories
│
├── tests/
│   └── fairness_test_set.py      # same symptoms in different phrasings
│
└── docs/
    ├── architecture.md
    └── responsible_ai_notes.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.10 or higher
- A Gemini API key — get one free at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) (no credit card required)
- Git

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/mediguide.git
cd mediguide
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows (Command Prompt)
venv\Scripts\activate

# Windows (Git Bash)
source venv/Scripts/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 4. Set your environment variables

Copy the template and fill in your key:

```bash
cp .env.example .env
```

Edit `.env`:

```
GEMINI_API_KEY=your_key_here
JWT_SECRET_KEY=any_long_random_string_you_choose
```

On Windows Git Bash, export before running scripts:

```bash
export GEMINI_API_KEY=your_key_here
export JWT_SECRET_KEY=your_secret_here
```

### 5. Ingest the knowledge base

This only needs to be run once. It chunks the documents and builds the Chroma vector store:

```bash
python agents/retrieval_agent/ingest.py
```

You should see confirmation that documents were chunked and stored. A `chroma_db/` folder will appear inside `agents/retrieval_agent/`.

---

## Running the System

### Option A — Full system via FastAPI + Streamlit UI

**Terminal 1** — start the API server:

```bash
uvicorn api.main:app --reload
```

**Terminal 2** — start the UI:

```bash
streamlit run ui/app.py
```

Open `http://localhost:8501` in your browser. Log in with your credentials, then ask a health question.

### Option B — Quick smoke test (no UI needed)

Test the end-to-end pipeline from the terminal:

```bash
python agents/triage_agent/test_triage.py
```

This runs two queries — one routine, one red-flag — and prints the results directly.

### Option C — Test individual agents

Test the retrieval agent alone:

```bash
python agents/retrieval_agent/test_client.py
```

Test the safety agent alone:

```bash
python agents/safety_agent/test_client.py
```

> **Note:** Always run scripts from the project root (`mediguide/`), not from inside a subfolder. Running from a subfolder causes `ModuleNotFoundError: No module named 'agents'`.

---

## API Reference

### `POST /login`

Returns a JWT access token.

**Request body:**

```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

---

### `POST /ask`

Submits a health question. Requires a valid JWT in the Authorization header.

**Headers:**

```
Authorization: Bearer <token>
```

**Request body:**

```json
{
  "query": "What are the common triggers for migraines?"
}
```

**Response — normal answer:**

```json
{
  "type": "answer",
  "answer": "Common migraine triggers include... [Source: migraine.md]",
  "sources": ["migraine.md"]
}
```

**Response — emergency escalation:**

```json
{
  "type": "escalation",
  "message": "Chest pain can indicate a heart attack or other serious cardiac event. Seek emergency care immediately."
}
```

**Error responses:**

- `401 Unauthorized` — missing or invalid JWT token
- `400 Bad Request` — query failed input sanitization (too long, injection attempt, etc.)

---

## Responsible AI

MediGuide was designed with Responsible AI principles embedded at every stage, not added as an afterthought.

### Transparency

- Every answer cites the specific source document chunk it was drawn from
- Users are shown a disclaimer on first use: _"This system provides general health information only. It is not a medical diagnosis. Always consult a qualified healthcare professional."_
- The system explicitly states when it does not have relevant information rather than guessing

### Safety

- The safety agent runs on every query before any retrieval or generation — there is no path to an LLM response that bypasses the safety check
- Emergency escalation messages direct users to professional care, not to the LLM
- The knowledge base is fixed and curated — the system cannot retrieve from arbitrary web sources

### Fairness

- Fairness testing (`tests/fairness_test_set.py`) checks that the same symptom described formally ("cephalgia"), informally ("really bad headache"), and in simplified English ("my head hurts a lot") all return equivalent retrieval quality
- spaCy NER is used to normalise query terms before embedding, reducing the gap between phrasing styles

### Privacy

- No user queries are logged or stored by default
- If session history is stored, it is encrypted at rest using Fernet symmetric encryption before being written to disk
- JWT tokens are short-lived and signed with a server-side secret that is never committed to the repository

### Explainability

- The triage agent's decision logic is explicit and deterministic (check safety → retrieve → generate), not a black box
- Source citations in every answer let users verify what the LLM was working from

Full notes: [`docs/responsible_ai_notes.md`](docs/responsible_ai_notes.md)

---

## Commercialization

**Business model:** B2B licensing to healthcare providers

**Target customers:**

- Private clinics wanting a pre-consultation information layer
- Telehealth platforms looking to reduce time spent on routine information queries
- Corporate wellness programs providing employee health support

**Pricing model:**

- Per-seat monthly subscription for small clinics
- Per-API-call pricing for telehealth platforms integrating via the REST API
- Enterprise licensing for large healthcare networks

**Why B2B over direct-to-consumer:** Liability and trust are easier to manage when a licensed healthcare provider is the customer. The provider takes responsibility for appropriate use within their platform, and MediGuide is positioned as a tool that supports their staff and patients rather than replacing clinical judgment.

**Deployment options:**

- Cloud-hosted SaaS (provider accesses via API key)
- On-premise deployment for providers with strict data residency requirements
- White-label integration into existing patient portals
