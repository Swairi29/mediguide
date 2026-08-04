"""
Week 3 — NER module.

Plain en_core_web_sm knows general-purpose entity types (PERSON, ORG, DATE,
GPE, ...) but has never heard of "wheezing" or "migraine" as a concept — try
it yourself and you'll see it tags almost nothing useful in a health query.

The standard spaCy fix for this is an EntityRuler: a rule-based pipeline
component you add *in front of* the statistical NER model, which lets you
define your own entity labels from a term list. Once it's added, calling
nlp(text).ents behaves exactly as the plan describes — it just now also
recognizes SYMPTOM and CONDITION spans, because we taught it to.

Where the term list comes from: pulled directly from the Symptoms/Causes
sections of the 5 documents in data/sources/, so the entities this module
can recognize line up with what your knowledge base can actually answer
about. If you add a 6th condition doc later, add its terms here too.
"""

import spacy
from spacy.pipeline import EntityRuler  # noqa: F401  (imported for clarity/reference)

SYMPTOM_TERMS = [
    "headache", "migraine", "throbbing pain", "nausea", "vomiting",
    "sensitivity to light", "photophobia", "sensitivity to sound", "phonophobia",
    "aura", "fatigue",
    "runny nose", "stuffy nose", "blocked nose", "sneezing", "sore throat",
    "cough", "dry cough", "fever", "high fever", "chills", "body aches",
    "muscle pain", "shortness of breath", "wheezing", "chest tightness",
    "chest pain", "difficulty breathing",
    "increased thirst", "frequent urination", "blurred vision",
    "slow-healing cuts", "numbness", "tingling", "weight loss",
    "itchy eyes", "watery eyes", "red eyes", "itchy throat", "postnasal drip",
    "dizziness", "confusion",
]

CONDITION_TERMS = [
    "migraine", "common cold", "cold", "flu", "influenza",
    "type 2 diabetes", "diabetes", "asthma",
    "seasonal allergies", "allergic rhinitis", "hay fever",
]

_nlp = None  # lazy-loaded singleton so we only load the model once per process


def get_nlp():
    """Loads en_core_web_sm once and attaches the EntityRuler, if not already done."""
    global _nlp
    if _nlp is not None:
        return _nlp

    nlp = spacy.load("en_core_web_sm")

    # Add the EntityRuler before the statistical "ner" component so our
    # rule-based matches win for these specific terms.
    ruler = nlp.add_pipe("entity_ruler", before="ner")

    patterns = []
    for term in SYMPTOM_TERMS:
        patterns.extend(_make_patterns("SYMPTOM", term))
    for term in CONDITION_TERMS:
        patterns.extend(_make_patterns("CONDITION", term))

    ruler.add_patterns(patterns)

    _nlp = nlp
    return _nlp


def _make_patterns(label: str, term: str):
    """
    Builds one or more EntityRuler patterns for `term`.

    Multi-word phrases ("shortness of breath") use per-token LOWER
    matching — plurals aren't a real concern for phrases like this.

    Single words are trickier: a LEMMA-only pattern misses cases like
    "sneezing" whenever spaCy's POS tagger reads it as a verb rather than a
    noun in that sentence (lemma becomes "sneeze", not "sneezing") — this
    happens inconsistently depending on surrounding words. So single words
    get *two* patterns: an exact LOWER match (catches the term as written)
    plus a LEMMA match (catches plurals like "migraines" -> "migraine").
    Matching either is enough; spaCy merges any overlapping hits into one
    entity span, so listing both never causes double-counting.
    """
    words = term.split()
    if len(words) == 1:
        return [
            {"label": label, "pattern": [{"LOWER": words[0]}]},
            {"label": label, "pattern": [{"LEMMA": words[0]}]},
        ]
    return [{"label": label, "pattern": [{"LOWER": w} for w in words]}]


def extract_medical_entities(text: str):
    """
    Returns a list of (entity_text, label) tuples found in `text`, where
    label is one of SYMPTOM, CONDITION, or any of spaCy's built-in labels
    (DATE, PERSON, etc. — harmless to keep, occasionally useful e.g. "since
    yesterday").
    """
    nlp = get_nlp()
    doc = nlp(text.lower())
    return [(ent.text, ent.label_) for ent in doc.ents]


def refine_query(text: str) -> str:
    """
    Builds a search-friendlier version of the raw user query.

    Free-text questions carry a lot of filler ("I've had a bad ... since
    yesterday, what could be causing it") that dilutes the embedding.
    Pulling out just the SYMPTOM/CONDITION entities and appending them to
    the original text re-weights the embedding toward the medically
    relevant terms, without throwing away the original phrasing (which
    still helps for queries with no recognized entities at all).
    """
    entities = extract_medical_entities(text)
    medical_terms = [ent_text for ent_text, label in entities if label in ("SYMPTOM", "CONDITION")]

    if not medical_terms:
        return text  # nothing recognized — fall back to the raw query

    # De-duplicate while preserving order.
    seen = set()
    unique_terms = []
    for term in medical_terms:
        if term not in seen:
            seen.add(term)
            unique_terms.append(term)

    return text + " | key terms: " + ", ".join(unique_terms)


if __name__ == "__main__":
    # Quick manual check: python ner.py
    test_queries = [
        "I have had a bad headache and fever since yesterday, what could be causing it",
        "what causes migraines",
        "shortness of breath and wheezing when I exercise",
        "I get itchy watery eyes and sneezing every spring",
    ]
    for q in test_queries:
        print(f"Query: {q!r}")
        print("  entities:", extract_medical_entities(q))
        print("  refined :", refine_query(q))
        print()