"""
Week 2 — Ingestion script.

Reads every .md file in data/sources/, splits each into ~200-500 word chunks,
and stores those chunks in a local Chroma collection (persisted to disk so you
don't have to re-ingest every time you run a query).

Usage:
    python ingest.py
"""

import os
import glob
import chromadb

# --- Paths -------------------------------------------------------------
# Adjust these if you move this script relative to your repo root.
SOURCES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sources")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

MAX_CHUNK_WORDS = 500
MIN_MERGE_WORDS = 60  # sections smaller than this get merged into a neighbor


def _split_into_paragraph_chunks(text: str, max_words: int):
    """Fallback splitter: groups paragraphs until max_words is hit. Used only
    when a single section is longer than MAX_CHUNK_WORDS."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current, count = [], [], 0
    for para in paragraphs:
        words = len(para.split())
        if count + words > max_words and current:
            chunks.append("\n\n".join(current))
            current, count = [], 0
        current.append(para)
        count += words
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def chunk_text(text: str, max_words=MAX_CHUNK_WORDS, min_merge_words=MIN_MERGE_WORDS):
    """
    Splits a markdown document into chunks along its "## " section headers,
    since each section (Overview, Causes, Symptoms, ...) is already a
    coherent, topically distinct unit — a much better chunk boundary than an
    arbitrary word count for structured reference documents like these.

    Rules:
    - Each "## " section becomes its own chunk (with its "# Title" folded
      into the first section, so every chunk still knows what document/
      condition it belongs to).
    - If a section is longer than max_words, it gets split further by
      paragraph (reusing the simple word-count approach).
    - Tiny sections (under min_merge_words) get merged into the next chunk
      so we don't end up with a near-empty, low-signal embedding.
    """
    import re

    # Split right before each "## " heading, keeping the heading attached.
    raw_sections = re.split(r"\n(?=## )", text.strip())
    raw_sections = [s.strip() for s in raw_sections if s.strip()]
    if not raw_sections:
        return []

    # raw_sections[0] is just the document preamble (the "# Title" line,
    # occasionally plus an intro line) — fold it into the first real
    # section instead of emitting a near-empty chunk of just the title.
    if len(raw_sections) > 1:
        body_sections = [raw_sections[0] + "\n" + raw_sections[1]] + raw_sections[2:]
    else:
        body_sections = raw_sections

    title_line = raw_sections[0].split("\n", 1)[0]

    sections = []
    for i, sec in enumerate(body_sections):
        if i == 0:
            sections.append(sec)  # already includes the title
        else:
            sections.append(f"{title_line}\n{sec}")

    # Split any oversized section further.
    expanded = []
    for sec in sections:
        if len(sec.split()) > max_words:
            expanded.extend(_split_into_paragraph_chunks(sec, max_words))
        else:
            expanded.append(sec)

    # Merge sections that are too small to carry much meaning on their own.
    merged = []
    for sec in expanded:
        if merged and len(sec.split()) < min_merge_words:
            merged[-1] = merged[-1] + "\n\n" + sec
        else:
            merged.append(sec)

    return merged


def load_documents(sources_dir: str):
    """Returns a list of (filename, full_text) for every .md file found."""
    docs = []
    for path in sorted(glob.glob(os.path.join(sources_dir, "*.md"))):
        with open(path, "r", encoding="utf-8") as f:
            docs.append((os.path.basename(path), f.read()))
    return docs


def main():
    print(f"Loading documents from: {os.path.abspath(SOURCES_DIR)}")
    docs = load_documents(SOURCES_DIR)
    if not docs:
        print("No .md files found — check SOURCES_DIR path.")
        return

    # Persistent client: writes an on-disk DB so the collection survives
    # between script runs (no need to re-embed every time you query).
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # get_or_create so re-running ingest.py doesn't error if the collection
    # already exists. We delete+recreate here so re-ingesting always starts
    # clean (useful while you're still editing source documents).
    try:
        client.delete_collection("health_info")
    except Exception:
        pass
    collection = client.create_collection(
        name="health_info",
        metadata={"hnsw:space": "cosine"},
    )

    all_chunks = []
    all_ids = []
    all_metadatas = []

    for filename, text in docs:
        chunks = chunk_text(text)
        print(f"  {filename}: {len(chunks)} chunk(s)")
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{filename}-{i}")
            all_metadatas.append({"source": filename, "chunk_index": i})

    # Chroma will embed these automatically using its default embedding
    # function (a local sentence-transformers model — no API key needed).
    collection.add(
        documents=all_chunks,
        ids=all_ids,
        metadatas=all_metadatas,
    )

    print(f"\nIngested {len(all_chunks)} chunks from {len(docs)} documents into "
          f"Chroma collection 'health_info' at {os.path.abspath(CHROMA_DIR)}")


if __name__ == "__main__":
    main()
