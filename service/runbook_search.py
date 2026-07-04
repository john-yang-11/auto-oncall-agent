"""
M4: RAG-based runbook retrieval.

Embed every runbook once at import time, embed the incoming alert text the
same way, and find the closest match by cosine similarity -- computed by
hand (no vector DB, no LangChain) since there are only 5 documents. Below
MATCH_THRESHOLD, treat it as "no confident match" rather than forcing a
guess.
"""
import os

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNBOOKS_DIR = os.path.join(ROOT, "runbooks")
MATCH_THRESHOLD = 0.35

_model = SentenceTransformer("all-MiniLM-L6-v2")


def _load_runbooks():
    docs = []
    for filename in sorted(os.listdir(RUNBOOKS_DIR)):
        if filename.endswith(".md"):
            with open(os.path.join(RUNBOOKS_DIR, filename)) as f:
                docs.append((filename, f.read()))
    return docs


_runbooks = _load_runbooks()
_runbook_embeddings = _model.encode([text for _, text in _runbooks])


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search(query: str):
    """Return (filename, score, text) for the best-matching runbook, or None
    if nothing clears MATCH_THRESHOLD."""
    query_embedding = _model.encode(query)
    scores = [cosine_similarity(query_embedding, doc_emb) for doc_emb in _runbook_embeddings]
    best_idx = int(np.argmax(scores))
    best_score = scores[best_idx]

    if best_score < MATCH_THRESHOLD:
        return None

    filename, text = _runbooks[best_idx]
    return {"filename": filename, "score": best_score, "text": text}


if __name__ == "__main__":
    for query in [
        "Error rate 71% on GET /<code>, exceeds 20% threshold",
        "Requests to /checkout are timing out under load",
        "This is about lunch orders and pizza toppings",
    ]:
        result = search(query)
        print(f"\nQuery: {query!r}")
        if result:
            print(f"  -> {result['filename']} (score={result['score']:.2f})")
        else:
            print("  -> no confident match")
