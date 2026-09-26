"""Reject ambiguous JSON objects and non-standard numeric constants."""

from decimal import Decimal, InvalidOperation


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON property")
        result[key] = value
    return result


def reject_json_constant(value):
    raise ValueError("non-standard JSON numeric constant")


# Preserve other input fields when a numeric token cannot be represented.
_INVALID_NUMBER = object()


def input_decimal(token):
    try:
        return Decimal(token)
    except InvalidOperation:
        return _INVALID_NUMBER


def input_integer(token):
    try:
        return int(token)
    except ValueError:
        return _INVALID_NUMBER
