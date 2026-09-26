"""Screen supplied payment and relationship facts without determining filing duties."""

from decimal import Decimal


def check(c: dict, oa_skill: dict) -> dict:
    base = {
        "oa_skill": oa_skill.get("slug"), "oa_skill_name": oa_skill.get("name"),
        "provenance": oa_skill.get("provenance", "unverified"),
        "reported_metadata": {key: oa_skill.get(key) for key in ("tier", "verifier", "source")},
        "amount_threshold_met": None, "threshold": None,
    }
    findings = []
    rules = oa_skill.get("rules", {})
    expected = {"schema": "contractor-payment-screen-v1",
                "payment_thresholds_usd": {"2025": "600", "2026": "2000"}}
    us_person = c["us_person"]
    if rules != expected:
        findings.append({"category": "amount", "status": "incomplete",
                         "text": "Unsupported rule contract. Only the documented 2025 and 2026 payment screens are supported."})
    elif us_person is False:
        findings.append({"category": "amount", "status": "info",
                         "text": "The US-person payment threshold is not applied to this reported foreign person."})
    elif us_person is None:
        findings.append({"category": "amount", "status": "incomplete",
                         "text": "US-person status is unknown; country does not establish it."})
    else:
        missing = []
        threshold = rules["payment_thresholds_usd"].get(str(c["payment_year"]))
        if threshold is None:
            missing.append("supported payment year")
        if c["ytd_paid"] is None:
            missing.append("eligible-payment amount")
        if c["currency"] != "USD":
            missing.append("explicit USD currency")
        if c["payment_basis"] != "eligible_nonemployee_services":
            missing.append("eligible nonemployee-service payment basis")
        if missing:
            findings.append({"category": "amount", "status": "incomplete",
                             "text": "Missing or unsupported: " + ", ".join(missing) + "."})
        else:
            base["threshold"] = Decimal(threshold)
            base["amount_threshold_met"] = c["ytd_paid"] >= base["threshold"]
            comparison = "meets" if base["amount_threshold_met"] else "is below"
            findings.append({"category": "amount", "status": "review" if base["amount_threshold_met"] else "info",
                             "text": f"The supplied {c['payment_year']} amount {comparison} the inclusive "
                                     f"${base['threshold']:,.0f} threshold. Filing requirements and exceptions need separate assessment."})
    form = c["form_on_file"]
    if us_person is True:
        documented = form == "W-9"
        wording = "W-9 reported present; validity has not been checked." if documented else (
            f"Reported form: {form}; W-9 status needs review." if form else "No W-9 reported in the input.")
        findings.append({"category": "documentation", "status": "info" if documented else "review", "text": wording})
    elif us_person is False:
        findings.append({"category": "documentation", "status": "info" if form else "review",
                         "text": f"Reported foreign-person form: {form}; suitability and validity need assessment."
                                 if form else "No foreign-person form reported; the suitable form needs assessment."})
    else:
        findings.append({"category": "documentation", "status": "incomplete",
                         "text": f"Reported form: {form or 'none'}; US-person status is needed to assess documentation."})
    if us_person is True:
        findings.append({"category": "services", "status": "info",
                         "text": "The foreign-person services screen is not applied to this reported US person."})
    elif c["services_in_us"] is None:
        findings.append({"category": "services", "status": "incomplete",
                         "text": "Service location is unknown."})
    elif c["services_in_us"]:
        findings.append({"category": "services", "status": "review",
                         "text": "US services are reported. Review sourcing, documentation and withholding even if a form is present."})
    else:
        findings.append({"category": "services", "status": "info",
                         "text": "The input reports no US services; no treaty or withholding conclusion is made."})
    relationship = c["full_time_exclusive"]
    if relationship is None:
        findings.append({"category": "relationship", "status": "incomplete",
                         "text": "Full-time and exclusive work status is unknown."})
    elif relationship:
        findings.append({"category": "relationship", "status": "review",
                         "text": "Full-time and exclusive work is a relationship-review trigger, not a worker-classification or permanent-establishment conclusion."})
    else:
        findings.append({"category": "relationship", "status": "info",
                         "text": "This particular relationship trigger is not reported; other classification factors are not assessed."})
    complete = not c.get("input_errors") and all(row["status"] != "incomplete" for row in findings)
    review = any(row["status"] == "review" for row in findings)
    return {**base, "findings": findings, "complete": complete,
            "status": "incomplete" if not complete else "warn" if review else "info",
            "headline": "Payment and relationship facts screened" if complete else "Screen incomplete",
            "detail": " ".join(row["text"] for row in findings)}
