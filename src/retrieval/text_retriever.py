from __future__ import annotations

import math
import re
from collections import Counter


def _terms(text: str) -> list[str]:
    tokens = re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE)
    return tokens + [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    common = left.keys() & right.keys()
    numerator = sum(left[key] * right[key] for key in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def retrieve_documents(query: str, documents: list[dict], top_k: int = 6) -> list[dict]:
    """Rank supplied documents with a transparent lexical relevance score."""
    if not documents:
        return []

    texts = [str(doc.get("text") or doc.get("title") or "") for doc in documents]
    query_terms = _terms(query)
    document_terms = [_terms(text) for text in texts]
    document_count = len(document_terms)

    document_frequency: Counter[str] = Counter()
    for terms in document_terms:
        document_frequency.update(set(terms))

    def vectorize(terms: list[str]) -> dict[str, float]:
        counts = Counter(terms)
        total = max(1, sum(counts.values()))
        return {
            term: (count / total)
            * (math.log((1 + document_count) / (1 + document_frequency.get(term, 0))) + 1.0)
            for term, count in counts.items()
        }

    query_vector = vectorize(query_terms)
    ranked = [
        (_cosine(query_vector, vectorize(terms)), index)
        for index, terms in enumerate(document_terms)
    ]
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [
        documents[index] | {"retrieval_score": float(score)}
        for score, index in ranked[:top_k]
    ]
