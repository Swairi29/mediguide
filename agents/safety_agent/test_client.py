# agents/safety_agent/test_client.py
import asyncio
import subprocess
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Build absolute path to server.py regardless of where you run this from
SERVER_SCRIPT = str(Path(__file__).parent / "server.py")


async def main():
    #launches server.py as a subprocess
    server_params = StdioServerParameters(
        command=sys.executable,  # uses the same python that's running this script
        args=[SERVER_SCRIPT],
    )

#connects to that process over stdio (MCP's transpprt layer)
    async with stdio_client(server_params) as (read, write):

        #4. does the MCP handshake and initializes the session
        async with ClientSession(read, write) as session:
            await session.initialize()

            #these goes over MCP, not the direct function call
            # Test 1: should escalate
            result = await session.call_tool(
                "check_safety",
                {"query": "I have severe chest pain and can't breathe"}
            )
            print("Test 1 (should escalate):")
            print(result.content[0].text)
            print()

            # Test 2: should NOT escalate
            result = await session.call_tool(
                "check_safety",
                {"query": "what foods help with migraines?"}
            )
            print("Test 2 (should NOT escalate):")
            print(result.content[0].text)
            print()

            # Test 3: edge case — capitalisation
            result = await session.call_tool(
                "check_safety",
                {"query": "I think I might be having a Seizure"}
            )
            print("Test 3 (capitalised keyword, should escalate):")
            print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())

# Proves the MCP server works correctly. Not just the checker logic inn isolation, but the whole chain of start the server >> connect to it >> call the tool over MCP >> get the result
# Python → launches server.py as a SUBPROCESS → connects to it over MCP protocol → sends check_safety as an MCP tool call → reads the response back  (whole MCP communication)