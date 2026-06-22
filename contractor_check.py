"""Check a contractor payment against the loaded OA rules.

The catches when you pay people across borders:
  - a "contractor" working **full-time and exclusively** looks like an employee —
    misclassification + permanent-establishment (PE) risk in their country
  - a **US contractor** paid over $600 needs a **W-9** and a **1099-NEC**
  - a **foreign contractor** needs a **W-8BEN** on file (no 1099); if the work is
    performed in the US, US-source withholding can apply

DELIBERATE SCOPE: a risk/obligation signal, not a full classification opinion or
treaty analysis. Production leans on the full OA skill + an agent step; the
named-CPA sign-off makes it relianceable.
"""

from __future__ import annotations


def check(c: dict, oa_skill: dict) -> dict:
    rules = oa_skill.get("rules", {})
    base = {"oa_skill": oa_skill.get("slug"), "oa_skill_name": oa_skill.get("name"),
            "tier": oa_skill.get("tier"), "verifier": oa_skill.get("verifier")}
    threshold = rules.get("form_1099_threshold", 600.0)
    wh = rules.get("us_source_withholding", 0.30)

    # Most severe first: misclassification / PE risk.
    if c["full_time_exclusive"]:
        where = c["country"] or "their country"
        return {**base, "status": "warn",
                "headline": "Misclassification / permanent-establishment risk",
                "detail": f"A full-time, exclusive '{('contractor' )}' in {where} looks like an employee — risking reclassification, back payroll taxes, and a taxable presence (PE) for the company there. Consider an EOR or a local entity."}

    if c["us_person"]:
        if c["ytd_paid"] > threshold and c["form_on_file"] != rules.get("us_person_form", "W-9"):
            return {**base, "status": "warn",
                    "headline": f"1099-NEC required — no W-9 on file",
                    "detail": f"Paid ${c['ytd_paid']:,.0f} (> ${threshold:,.0f}). Collect a W-9 and issue a 1099-NEC for this US contractor."}
        return {**base, "status": "ok",
                "headline": "US contractor — W-9 on file, 1099 will issue",
                "detail": f"${c['ytd_paid']:,.0f} paid; documentation in order."}

    # Foreign person
    if c["form_on_file"] != rules.get("foreign_person_form", "W-8BEN"):
        extra = f" Services performed in the US can trigger {wh:.0%} US-source withholding (or a treaty rate)." if c["services_in_us"] else ""
        return {**base, "status": "warn",
                "headline": "Foreign contractor — no W-8BEN on file",
                "detail": f"Get a W-8BEN on file (foreign persons get no 1099).{extra}"}
    return {**base, "status": "ok",
            "headline": "Foreign contractor — W-8BEN on file",
            "detail": f"${c['ytd_paid']:,.0f} paid; no 1099 required, documentation in order."}
