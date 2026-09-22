"""Deel contractor extraction.

In live mode (DEEL_API_TOKEN) this would pull contractors/payments from Deel's
API (free self-serve sandbox at demo.deel.com). For the demo it loads bundled
samples in a similar shape and normalizes each to the facts the tax-obligation
check needs.
"""

from __future__ import annotations

import json
import os

DEEL_API_TOKEN = os.environ.get("DEEL_API_TOKEN")


def extract(source: str) -> list[dict]:
    if DEEL_API_TOKEN:
        return _extract_live()
    with open(source) as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else [data]


def _extract_live() -> list[dict]:  # pragma: no cover - needs a sandbox token
    """Live Deel pull. Wired but inert until DEEL_API_TOKEN is present.

        GET https://api.letsdeel.com/rest/v2/contracts
    """
    import urllib.request

    req = urllib.request.Request(
        "https://api.letsdeel.com/rest/v2/contracts?limit=25",
        headers={"Authorization": f"Bearer {DEEL_API_TOKEN}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("data", [])


def normalize(c: dict) -> dict:
    return {
        "name": c.get("name", "Contractor"),
        "country": (c.get("country") or "").upper(),
        "us_person": bool(c.get("us_person", False)),
        "ytd_paid": float(c.get("ytd_paid", 0)),
        "payment_year": c.get("payment_year"),
        "form_on_file": c.get("form_on_file"),         # "W-9" | "W-8BEN" | null
        "services_in_us": bool(c.get("services_in_us", False)),
        "full_time_exclusive": bool(c.get("full_time_exclusive", False)),
    }
