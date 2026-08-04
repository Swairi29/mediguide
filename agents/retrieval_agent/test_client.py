"""
Week 3 — MCP test client.

This is your Week 3 "Done when" checkpoint: it starts server.py as a
subprocess, speaks the MCP protocol to it over stdio, lists the tools it
exposes, and calls search_health_info with a couple of test questions.

Usage:
    python test_client.py
"""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_DIR = Path(__file__).resolve().parent


async def main():
    server_params = StdioServerParameters(
        command=sys.executable,   # use the same Python interpreter (venv-safe)
        args=["server.py"],
        cwd=SERVER_DIR,            # run relative to this script, not the caller's cwd
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools exposed by the server:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description.strip().splitlines()[0]}")
            print()

            test_queries = [
                "what causes migraines",
                "I have shortness of breath and wheezing",
            ]

            for query in test_queries:
                print(f"Calling search_health_info(query={query!r})")
                result = await session.call_tool(
                    "search_health_info",
                    arguments={"query": query, "k": 3},
                )
                # result.content is a list of content blocks; structuredContent
                # (when present) holds the actual returned Python value.
                hits = result.structuredContent.get("result", result.structuredContent) \
                    if result.structuredContent else result.content
                print(hits)
                print()


if __name__ == "__main__":
    asyncio.run(main())