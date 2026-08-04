"""
Week 2/3 — Query script (CLI).

Loads the Chroma collection built by ingest.py and runs a plain-text query
against it, printing the top-3 most relevant chunks. As of Week 3, the
query is first refined with NER-extracted symptom/condition terms (see
ner.py) before being embedded and searched (see retrieval.py).

Usage:
    python query.py "what causes migraines"

If you don't pass an argument, it falls back to a default test query.
"""

import sys
from retrieval import search_health_info, DEFAULT_K
from ner import extract_medical_entities


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "what causes migraines"
    print(f"Query: {query!r}")

    entities = extract_medical_entities(query)
    if entities:
        print(f"Recognized entities: {entities}")
    else:
        print("Recognized entities: none (falling back to raw query)")
    print()

    hits = search_health_info(query, k=DEFAULT_K)
    for rank, hit in enumerate(hits, start=1):
        print(f"#{rank}  source={hit['source']}  chunk={hit['chunk_index']}  distance={hit['distance']:.3f}")
        print("-" * 60)
        print(hit["text"])
        print()


if __name__ == "__main__":
    main()