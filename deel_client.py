"""Read the documented payment-summary JSON format, with no implicit provider calls."""

from decimal import Decimal, InvalidOperation
import json

from json_contract import input_decimal, input_integer, reject_json_constant, unique_object


def boolean(value, field):
    if value is not None and not isinstance(value, bool):
        raise ValueError(f"{field} must be true, false or null")
    return value


def text(value, field):
    if value is not None and not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    return value.strip() if value is not None else None


def payment(value, field="ytd_paid"):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a number, not a Boolean")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f"{field} must be a decimal amount") from error
    if not result.is_finite() or result < 0 or result > Decimal("1e12"):
        raise ValueError(f"{field} must be finite and between 0 and 1e12")
    if result.as_tuple().exponent < -2:
        raise ValueError(f"{field} supports at most two decimal places")
    return result


def extract(source: str) -> list[dict]:
    with open(source, encoding="utf-8") as fh:
        data = json.load(fh, parse_float=input_decimal, parse_int=input_integer,
                         parse_constant=reject_json_constant, object_pairs_hook=unique_object)
    if data == []:
        raise ValueError("input must contain at least one record")
    return data if isinstance(data, list) else [data]


def calendar_year(value, field):
    if value is not None and (type(value) is not int or not 1 <= value <= 9999):
        raise ValueError(f"{field} must be a calendar-year integer")
    return value


def normalize(c: dict, *, partial=False) -> dict:
    if not isinstance(c, dict):
        raise ValueError("each contractor summary must be an object")
    converters = {"name": text, "country": text, "currency": text,
                  "payment_basis": text, "form_on_file": text,
                  "us_person": boolean, "services_in_us": boolean, "full_time_exclusive": boolean,
                  "ytd_paid": payment, "payment_year": calendar_year}
    facts, errors = {}, []
    for field, convert in converters.items():
        try:
            facts[field] = convert(c.get(field), field)
        except ValueError as error:
            if not partial:
                raise
            facts[field] = None
            errors.append(str(error))
    facts["name"] = facts["name"] or "Unnamed contractor"
    for field in ("country", "currency"):
        facts[field] = facts[field].upper() if facts[field] else None
    return {**facts, "input_errors": errors}
