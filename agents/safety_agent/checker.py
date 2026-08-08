# agents/safety_agent/checker.py
# This has the actual safety logic
import json
from pathlib import Path

# Load red_flags.json once at import time, not on every call
_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "red_flags.json"

with open(_DATA_PATH, encoding="utf-8") as f:
    _RED_FLAGS = json.load(f)["red_flags"]


def check_safety(query: str) -> dict:
    """
    Check whether a query contains emergency red-flag keywords.

    Returns:
        {"escalate": bool, "reason": str}
        escalate=True means the triage agent should NOT answer normally
        and should return the reason message to the user instead.
    """
    query_lower = query.lower() 
    #  all becomes simple lowercase for easier matching

    # Check for red-flag keywords in the query

    for entry in _RED_FLAGS:
        for keyword in entry["keywords"]:
            if keyword in query_lower:
                return {
                    "escalate": True,
                    "reason": entry["reason"]
                }

    return {
        "escalate": False,
        "reason": ""
    }