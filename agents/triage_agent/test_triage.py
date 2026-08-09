# agents/triage_agent/test_triage.py
import sys
from pathlib import Path

# Add project root to path so 'agents' package is found
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.triage_agent.triage import ask

print("=" * 60)
print("Test 1: routine question (should get a cited answer)")
print("=" * 60)
result = ask("What foods should I avoid if I have migraines?")
print(f"Type   : {result['type']}")
if result["type"] == "answer":
    print(f"Sources: {result['sources']}")
    print(f"Answer :\n{result['answer']}")
else:
    print(f"Message: {result['message']}")

print()
print("=" * 60)
print("Test 2: red-flag question (should escalate, NO Gemini call)")
print("=" * 60)
result = ask("I have severe chest pain and I can't breathe")
print(f"Type   : {result['type']}")
if result["type"] == "escalation":
    print(f"Message: {result['message']}")
else:
    print(f"Answer : {result['answer']}")