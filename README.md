# Deel → OpenAccountants: illustrative contractor screening

Screen supplied payment, documentation, service-location and relationship facts.
Each finding remains visible independently. The example does not determine
filing, withholding, worker classification or permanent establishment, and its
bundled rules have no professional sign-off.

![Illustrative contractor screening](demo.svg)

## Run it

Python 3.10 or later and the standard library are sufficient.

```bash
python pipeline.py
python pipeline.py samples/contractors.json
python -m unittest discover -s tests -v
python make_svg.py
```

The default command and SVG generator use bundled examples. Empty, invalid or
incomplete input returns exit code 2. Other records and independent findings
remain visible. Exit code 0 means the supplied facts were screened completely;
review findings can still be present, and it does not mean legal compliance.

An invalid field retains a diagnostic and becomes unknown for its dependent
screen. Other usable facts for the same contractor still produce findings.
Non-object records are rejected as a whole. Control characters in supplied
text are displayed as escapes, and redirected output tolerates limited encodings.

## What the screen covers

| Finding | Scope |
|---|---|
| Amount | Inclusive payment threshold for a reported US person and a supported payment year |
| Documentation | Reported form presence; suitability and validity remain unverified |
| Services | Review of reported US services by a foreign person, even when a form is present |
| Relationship | Full-time and exclusive work triggers review without determining employment or permanent establishment |

A missing W-9 stays visible below the payment threshold. A foreign-person form
does not suppress the US-services finding. No form is assumed to be suitable
for every foreign person, and country never substitutes for US-person status.

## Payment year and sources

The example compares eligible nonemployee-service payments in USD against
these inclusive thresholds:

| Payment year | Amount threshold |
|---|---|
| 2025 | US$600 or more |
| 2026 | US$2,000 or more |

The [IRS information-return guidance](https://www.irs.gov/businesses/small-businesses-self-employed/am-i-required-to-file-a-form-1099-or-other-information-return)
and [26 USC 6041](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section6041&num=0&edition=prelim)
support the change for payments after 31 December 2025. Sources were checked
on 26 September 2026. Later years remain unsupported because indexed thresholds
must be verified for the relevant year.

Meeting an amount threshold alone does not establish a filing duty. The input
must already identify eligible nonemployee-service payments; payer, payee,
payment-method and other exceptions need separate assessment. The example does
not calculate withholding, apply a treaty, prepare forms or make filings.

## JSON contract

This is a documented payment-summary format, not a verified Deel API payload.
The five sample contractors are fabricated.

- Supply `us_person`, `services_in_us` and `full_time_exclusive` as JSON Booleans
  or null. Missing status remains unknown; strings such as `"false"` are invalid.
- `payment_year` is an integer. The US-person amount screen supports 2025 and
  2026 only, with explicit `currency: "USD"` and
  `payment_basis: "eligible_nonemployee_services"`.
- `ytd_paid` is the supplied eligible-payment total for that calendar year.
  Numeric values and decimal strings must be finite, non-negative, at most
  `1e12` and have at most two decimal places. Explicit zero remains zero.
- `name`, `country` and `form_on_file` are text. Whitespace is trimmed; an empty
  form does not count as documentation. A reported W-9 is not proof of validity.

The previous `DEEL_API_TOKEN` path fetched a partial list of contracts without
the required payment facts. That implicit import has been removed. Export or
prepare the documented JSON explicitly; no live Deel import is included.

## Optional OpenAccountants adapter

`python pipeline.py --live` opts into the experimental JSON-RPC adapter and
requires `OA_MCP_TOKEN` configured outside the repository. Live authentication
and response handling have not been verified against the service. Failed live
calls never fall back to bundled examples.

Only the `contractor-payment-screen-v1` rules in `oa_client.py` supply supported
payment thresholds. Incompatible rules leave the amount screen incomplete
without hiding documentation, service-location or relationship findings.
Provider tier, verifier and source metadata remain reported information, not
independent attestation.

JSON inputs and provider responses reject duplicate object properties and
non-standard numeric constants instead of silently choosing a value.

## Files

| File | Role |
|---|---|
| `pipeline.py` | CLI and separate findings for each contractor |
| `deel_client.py` | Payment-summary JSON extraction and normalisation |
| `contractor_check.py` | Bounded payment and relationship screens |
| `oa_client.py` | Bundled examples and experimental live adapter |
| `samples/contractors.json` | Five fabricated contractor summaries |
| `reporting.py` | Visible control-character escapes and portable output |
| `json_contract.py` | JSON object and numeric-token validation |
| `tests/` | Offline calculation, adapter and command-line regressions |
