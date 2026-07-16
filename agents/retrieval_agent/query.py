"""
Week 2 — Query script.

Loads the Chroma collection built by ingest.py and runs a plain-text query
against it, printing the top-3 most relevant chunks.

Usage:
    python query.py "what causes migraines"

If you don't pass an argument, it falls back to a default test query.
"""

import os
import sys
import chromadb

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
TOP_K = 3


def search(query: str, k: int = TOP_K):
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection("health_info")

    results = collection.query(query_texts=[query], n_results=k)

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    return list(zip(docs, metas, distances))


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "what causes migraines"
    print(f"Query: {query!r}\n")

    hits = search(query)
    for rank, (doc, meta, dist) in enumerate(hits, start=1):
        print(f"#{rank}  source={meta['source']}  chunk={meta['chunk_index']}  distance={dist:.3f}")
        print("-" * 60)
        print(doc)
        print()


if __name__ == "__main__":
    main()
