from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import re

import requests

TIMEOUT = 8
DATE_RE = re.compile(r"^\s*(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s*$")


def _cell_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip().replace("&nbsp;", "")


def _number(cell: str) -> float | None:
    text = cell.strip().replace(",", "").replace("$", "").replace("£", "")
    if text in {"", "-", "—", "–"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    match = re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    value = float(text)
    return -abs(value) if negative else value


def _parse_date(label: str):
    m = DATE_RE.fullmatch(label.strip())
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %b %Y").date()
    except ValueError:
        return None


def _parse_rows(html: str) -> list[dict]:
    """Parse only complete daily rows and read Total from the final table cell.

    Farside has individual-fund columns containing many 0.0 / '-' values.  Dropping
    missing cells and then taking the 'last number' can silently select the wrong
    column.  We therefore preserve cell positions and require a numeric final Total.
    """
    parsed = []
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.I | re.S)
    for row in rows:
        cells = [_cell_text(x) for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.I | re.S)]
        if len(cells) < 3:
            continue
        day = _parse_date(cells[0])
        if day is None:
            continue
        total = _number(cells[-1])
        if total is None:
            continue
        parsed.append({
            "date": day,
            "date_label": cells[0],
            "total_musd": total,
            "raw_cells": cells[:16],
        })
    parsed.sort(key=lambda x: x["date"])
    return parsed



def _completed_rows(rows: list[dict], now: datetime | None = None) -> tuple[list[dict], list[dict]]:
    """Separate completed US sessions from the current New York calendar day.

    Farside can expose an in-progress row for the current US session (often 0.0
    early in the day).  Treating that row as a completed daily flow silently
    corrupts both the latest-session value and rolling 5-session sum.  BitScope
    therefore uses only dates strictly before the current New York date for
    decision evidence and reports today's row separately as provisional.
    """
    ref = now or datetime.now(timezone.utc)
    ny_today = ref.astimezone(ZoneInfo("America/New_York")).date()
    completed = [row for row in rows if row["date"] < ny_today]
    provisional = [row for row in rows if row["date"] >= ny_today]
    return completed, provisional

def fetch_etf_flow() -> dict:
    """Best-effort public US spot-BTC ETF flow snapshot from Farside.

    HTML sources can change, so parsing failure is explicitly returned as unavailable.
    The agent must not treat missing flow data as neutral evidence.
    """
    out = {
        "available": False,
        "provider": "Farside Investors",
        "source_url": "https://farside.co.uk/btc/",
        "errors": [],
    }
    try:
        response = requests.get(out["source_url"], timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0 btc-agent-v5"})
        response.raise_for_status()
        parsed = _parse_rows(response.text)
        completed, provisional = _completed_rows(parsed)
        if completed:
            latest = completed[-1]
            recent = completed[-5:]
            out.update({
                "available": True,
                "latest_date_label": latest["date_label"],
                "latest_total_musd": latest["total_musd"],
                "five_session_total_musd": sum(r["total_musd"] for r in recent),
                "recent_rows": [{"date_label": r["date_label"], "total_musd": r["total_musd"]} for r in completed[-7:]],
                "parser": "strict_completed_session_v5_0_2",
                "completion_policy": "current New York calendar day is provisional and excluded from decision evidence",
            })
            if provisional:
                latest_provisional = provisional[-1]
                out["provisional_date_label"] = latest_provisional["date_label"]
                out["provisional_total_musd"] = latest_provisional["total_musd"]
        else:
            out["errors"].append("Could not locate a completed dated ETF-flow row with a numeric Total cell.")
    except Exception as exc:
        out["errors"].append(f"etf_flow: {type(exc).__name__}: {exc}")
    out["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return out
