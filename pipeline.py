#!/usr/bin/env python3
"""Deel -> OpenAccountants contractor-tax pipeline.

    python pipeline.py                       # bundled sample contractors (mock mode)
    python pipeline.py samples/contractors.json

The flow:
    Deel contractors -> OA MCP (start -> get_skill) -> obligation/risk check -> verdict

Live: set OA_MCP_TOKEN (+ DEEL_API_TOKEN, free sandbox) to pull real contracts.
"""

from __future__ import annotations

import os
import sys

import deel_client
import contractor_check
from oa_client import OAClient

STATUS = {"ok": "✅", "warn": "⚠️ ", "info": "ℹ️ "}


def run(source: str, oa: OAClient) -> None:
    contractors = deel_client.extract(source)
    plan = oa.start("Check contractor tax obligations", "US")
    slug = (plan.get("skills_to_load") or [None])[0]
    skill = oa.get_skill(slug) if slug else {}

    for c in contractors:
        f = deel_client.normalize(c)
        kind = "US" if f["us_person"] else f["country"]
        tags = []
        if f["full_time_exclusive"]:
            tags.append("full-time/exclusive")
        if f["services_in_us"] and not f["us_person"]:
            tags.append("works in US")
        tag = f"  [{', '.join(tags)}]" if tags else ""
        print(f"\n🌍  {f['name']} · {kind} · ${f['ytd_paid']:,.0f} YTD · form: {f['form_on_file'] or 'none'}{tag}")

        v = contractor_check.check(f, skill)
        trust = f"tier {v.get('tier')}" + (f", signed off by {v['verifier']}" if v.get("verifier") else "")
        print(f"    OpenAccountants → {v.get('oa_skill_name') or 'contractor rules'}  ({trust})")
        print(f"    {STATUS.get(v['status'], '')} {v['headline']}")
        print(f"       {v['detail']}")


def main(argv: list[str]) -> int:
    oa = OAClient()
    mode = "LIVE" if oa.live else "MOCK (set OA_MCP_TOKEN + DEEL_API_TOKEN to go live)"
    print(f"Deel → OpenAccountants · contractor-tax demo  [{mode}]")
    here = os.path.dirname(os.path.abspath(__file__))
    source = argv[1] if len(argv) > 1 else os.path.join(here, "samples", "contractors.json")
    run(source, oa)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
