# agents/triage_agent/triage.py
import asyncio
import json
import sys
import os
from pathlib import Path
from google import genai

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Absolute paths to both server scripts — works regardless of where you run from
SAFETY_SERVER   = str(Path(__file__).parent.parent / "safety_agent"   / "server.py")
RETRIEVAL_SERVER = str(Path(__file__).parent.parent / "retrieval_agent" / "server.py")

# Gemini client — reads GEMINI_API_KEY from environment
gemini = genai.Client()


async def _run_triage(query: str) -> dict:
    """Full async pipeline: safety check → retrieval → Gemini answer."""

    # Step 1: Safety check (always first, no exceptions)
    safety_params = StdioServerParameters(
        command=sys.executable,
        args=[SAFETY_SERVER]
    )
    async with stdio_client(safety_params) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool("check_safety", {"query": query})
            safety = json.loads(result.content[0].text)

    # If emergency flagged — return immediately, never call retrieval or Gemini
    if safety["escalate"]:
        return {
            "type": "escalation",
            "message": safety["reason"]
        }

    # Step 2: Retrieve relevant chunks
    retrieval_params = StdioServerParameters(
        command=sys.executable,
        args=[RETRIEVAL_SERVER]
    )
    async with stdio_client(retrieval_params) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool(
                "search_health_info",
                {"query": query, "k": 3}
            )
            chunks = [json.loads(item.text) for item in result.content]

    # Step 3: Build RAG prompt
    # Build context block from chunks — adjust key names if your retrieval
    # agent returns different keys (check test_client.py output)
    context_parts = []
    for chunk in chunks:
        source = chunk.get("source", chunk.get("metadata", {}).get("source", "unknown"))
        text   = chunk.get("text",   chunk.get("document", ""))
        context_parts.append(f"[Source: {source}]\n{text}")

    context = "\n\n---\n\n".join(context_parts)

    prompt = (
        "You are MediGuide, a health information assistant. "
        "Your job is to answer the user's question using ONLY the context provided below. "
        "Do NOT add information from outside the context. "
        "Do NOT make a diagnosis. "
        "After each key point, cite the source in square brackets like [Source: filename]. "
        "If the context does not contain enough information to answer, say so clearly "
        "and suggest the user consult a healthcare professional.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {query}"
    )

    # Step 4: Call Gemini
    response = gemini.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=prompt
    )

    sources = []
    for chunk in chunks:
        s = chunk.get("source", chunk.get("metadata", {}).get("source", "unknown"))
        if s not in sources:
            sources.append(s)

    return {
        "type": "answer",
        "answer": response.text,
        "sources": sources
    }


def ask(query: str) -> dict:
    """
    Synchronous wrapper around the async pipeline.
    Call this from test scripts, FastAPI, and anywhere else.
    """
    return asyncio.run(_run_triage(query))