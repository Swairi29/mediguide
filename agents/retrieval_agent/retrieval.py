"""
Shared retrieval logic used by both query.py (plain CLI) and server.py (MCP
server). Keeping this in one place means the MCP tool and the CLI can never
drift apart in behavior.
"""

import os
import chromadb

from ner import refine_query

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
DEFAULT_K = 3


def search_health_info(query: str, k: int = DEFAULT_K):
    """
    Refines `query` with NER-extracted symptom/condition terms, searches the
    Chroma collection built by ingest.py, and returns the top-k chunks.

    Returns a list of dicts:
        {"source": str, "chunk_index": int, "text": str, "distance": float}
    ordered by relevance (lowest distance first).
    """
    refined = refine_query(query)

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection("health_info")

    results = collection.query(query_texts=[refined], n_results=k)

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        hits.append({
            "source": meta["source"],
            "chunk_index": meta["chunk_index"],
            "text": doc,
            "distance": dist,
        })
    return hits