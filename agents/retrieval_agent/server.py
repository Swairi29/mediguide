"""
Week 3 — MCP server.

Wraps the retrieval agent as an MCP server exposing one tool:
search_health_info(query, k) -> list of chunk dicts.

This is the "MCP server" role for the retrieval agent described in the
project plan: the triage agent (built in Week 5) will act as the MCP host
and call this tool over the protocol instead of importing retrieval.py
directly — that's the "defined agent communication protocol" your rubric
asks about.

Run standalone (keeps running, waiting for a client over stdio):
    python server.py

You won't see much printed when you run it directly — MCP servers speak
their protocol over stdin/stdout, not print() to the terminal. To actually
see it work, run test_client.py instead (see that file for details), which
starts this server as a subprocess and talks to it properly.
"""

from mcp.server.fastmcp import FastMCP

from retrieval import search_health_info as _search_health_info, DEFAULT_K

mcp = FastMCP("mediguide-retrieval")


@mcp.tool()
def search_health_info(query: str, k: int = DEFAULT_K) -> list[dict]:
    """
    Search MediGuide's health-information knowledge base for chunks
    relevant to a plain-text health question.

    Args:
        query: A plain-text health question, e.g. "what causes migraines".
        k: How many chunks to return (default 3).

    Returns:
        A list of chunk dicts, ordered most-to-least relevant:
        {"source": str, "chunk_index": int, "text": str, "distance": float}
    """
    return _search_health_info(query, k=k)


if __name__ == "__main__":
    mcp.run()  # defaults to stdio transport