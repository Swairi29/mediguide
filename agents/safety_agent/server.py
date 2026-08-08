# agents/safety_agent/server.py
from mcp.server.fastmcp import FastMCP
from checker import check_safety as _check_safety

mcp = FastMCP("safety-agent")

# docstring - the triage agent read this to understand the tool
@mcp.tool()
def check_safety(query: str) -> dict:
    """
    Check if a user query contains emergency red-flag symptoms.
    Returns {escalate: bool, reason: str}.
    If escalate is True, do not answer normally — return the reason to the user.
    """
    return _check_safety(query)


if __name__ == "__main__":
    mcp.run()