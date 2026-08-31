from __future__ import annotations

from datetime import datetime, timezone
import re

import requests

TIMEOUT = 8


def fetch_etf_flow() -> dict:
    """Best-effort public US spot-BTC ETF flow snapshot from Farside.

    HTML sources can change, so parsing failure is explicitly returned as unavailable.
    The agent must not treat missing flow data as neutral evidence.
    """
    out = {"available": False, "provider": "Farside Investors", "source_url": "https://farside.co.uk/btc/", "errors": []}
    try:
        response = requests.get(out["source_url"], timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0 btc-agent-v4"})
        response.raise_for_status()
        html = response.text
        # Strip tags into rows; capture rows that look like a date plus a total. This is intentionally defensive.
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.I | re.S)
        parsed = []
        for row in rows:
            cells = [re.sub(r"<[^>]+>", " ", x) for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.I | re.S)]
            cells = [re.sub(r"\s+", " ", x).strip().replace("&nbsp;", "") for x in cells]
            if len(cells) < 3:
                continue
            if not re.search(r"\d{1,2}\s+[A-Za-z]{3}|\d{1,2}/\d{1,2}|\d{4}", cells[0]):
                continue
            numeric = []
            for cell in cells[1:]:
                clean = cell.replace(",", "").replace("$", "").replace("£", "").replace("(", "-").replace(")", "")
                m = re.search(r"-?\d+(?:\.\d+)?", clean)
                numeric.append(float(m.group()) if m else None)
            values = [x for x in numeric if x is not None]
            if values:
                parsed.append({"date_label": cells[0], "values": values, "raw_cells": cells[:16]})
        if parsed:
            latest = parsed[-1]
            # Farside tables normally place Total in the last numeric column; retain raw row for auditability.
            total_musd = latest["values"][-1]
            recent_totals = [r["values"][-1] for r in parsed[-5:] if r.get("values")]
            out.update({
                "available": True,
                "latest_date_label": latest["date_label"],
                "latest_total_musd": total_musd,
                "five_session_total_musd": sum(recent_totals) if recent_totals else None,
                "recent_rows": [{"date_label": r["date_label"], "total_musd": r["values"][-1]} for r in parsed[-7:]],
            })
        else:
            out["errors"].append("Could not locate ETF-flow rows in the current HTML structure.")
    except Exception as exc:
        out["errors"].append(f"etf_flow: {type(exc).__name__}: {exc}")
    out["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return out
