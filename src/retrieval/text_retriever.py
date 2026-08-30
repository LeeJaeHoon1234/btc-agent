from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def retrieve_documents(query: str, documents: list[dict], top_k: int = 6) -> list[dict]:
    if not documents:
        return []
    texts = [str(doc.get("text") or doc.get("title") or "") for doc in documents]
    try:
        matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=4000).fit_transform([query] + texts)
        scores = cosine_similarity(matrix[0:1], matrix[1:]).ravel()
        order = scores.argsort()[::-1][:top_k]
        return [documents[int(i)] | {"retrieval_score": float(scores[int(i)])} for i in order]
    except ValueError:
        return documents[:top_k]
