from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import requests

TIMEOUT = 8


def _search_one(query: str, limit: int = 8) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    response = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    root = ET.fromstring(response.text)
    docs = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        source_node = item.find("source")
        source = (source_node.text or "Google News") if source_node is not None else "Google News"
        try:
            published_at = parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat() if pub else None
        except Exception:
            published_at = pub or None
        if title and link:
            docs.append({
                "title": title,
                "url": link,
                "source": source,
                "published_at": published_at,
                "text": f"{title} {source}",
                "query": query,
            })
    return docs


def search_btc_news(queries: list[str] | None = None, per_query: int = 8) -> dict:
    queries = queries or [
        "Bitcoin BTC market when:2d",
        "Bitcoin ETF Fed dollar Treasury when:2d",
        "Bitcoin regulation crypto policy when:7d",
    ]
    docs: list[dict] = []
    errors: list[str] = []
    seen = set()
    for query in queries:
        try:
            for doc in _search_one(query, per_query):
                key = doc["title"].lower()
                if key not in seen:
                    seen.add(key)
                    docs.append(doc)
        except Exception as exc:
            errors.append(f"{query}: {exc}")
    return {
        "available": bool(docs),
        "provider": "Google News RSS",
        "documents": docs,
        "errors": errors,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
