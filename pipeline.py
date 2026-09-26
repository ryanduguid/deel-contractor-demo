#!/usr/bin/env python3
"""Screen the documented contractor-payment JSON format using illustrative rules."""

import argparse
from pathlib import Path
import sys
import textwrap

import deel_client
import contractor_check
from oa_client import OAClient
from reporting import configure_output, safe_text


def run(source: str, oa: OAClient) -> bool:
    contractors = deel_client.extract(source)
    plan = oa.start("Screen supplied contractor payment and relationship facts", "US")
    if not isinstance(plan, dict):
        raise ValueError("start must return an object")
    skills = plan.get("skills_to_load", [])
    if not isinstance(skills, list) or any(not isinstance(slug, str) for slug in skills):
        raise ValueError("skills_to_load must be an array of names")
    skill = oa.get_skill(skills[0]) if skills else {}
    complete = True
    for index, contractor in enumerate(contractors, 1):
        try:
            facts = deel_client.normalize(contractor, partial=True)
            verdict = contractor_check.check(facts, skill)
        except ValueError as error:
            print(f"\nContractor {index}: invalid input: {safe_text(error)}")
            complete = False
            continue
        person = {True: "US person", False: "foreign person", None: "unknown US-person status"}[facts["us_person"]]
        amount = "unknown amount" if facts["ytd_paid"] is None else f"{facts['ytd_paid']:,.2f}"
        print(f"\n🌍  {safe_text(facts['name'])} · {person} · {safe_text(facts['country'] or 'unknown country')}")
        print(f"    {facts['payment_year'] or 'unknown year'} payments: {amount} "
              f"{safe_text(facts['currency'] or '(currency unknown)')} · reported form: {safe_text(facts['form_on_file'] or 'none')}")
        trust = ("unverified sample rules" if verdict["provenance"] == "sample"
                 else "provider metadata; not independently verified")
        print(f"    OpenAccountants → {safe_text(verdict.get('oa_skill_name') or 'contractor rules')} ({trust})")
        print(f"    {safe_text(verdict['headline'])}")
        for error in facts["input_errors"]:
            print(f"    invalid input: {safe_text(error)}")
        for finding in verdict["findings"]:
            marker = "ℹ️" if finding["status"] == "info" else "⚠️"
            print(textwrap.fill(f"{marker} {finding['category']}: {safe_text(finding['text'])}", width=96,
                                initial_indent="    ", subsequent_indent="       "))
        complete = complete and verdict["complete"] and not facts["input_errors"]
    return complete


def main(argv: list[str]) -> int:
    configure_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default=str(Path(__file__).parent / "samples/contractors.json"))
    parser.add_argument("--live", action="store_true", help="use the unverified OpenAccountants adapter")
    args = parser.parse_args(argv[1:])
    oa = OAClient() if args.live else OAClient(token=None)
    if args.live and not oa.live:
        parser.error("--live requires OA_MCP_TOKEN")
    mode = "LIVE ADAPTER (unverified)" if oa.live else "BUNDLED ILLUSTRATIVE RULES"
    print(f"Deel → OpenAccountants · contractor demo [{mode}]")
    try:
        complete = run(args.source, oa)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Screen failed: {safe_text(error)}", file=sys.stderr)
        return 2
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
