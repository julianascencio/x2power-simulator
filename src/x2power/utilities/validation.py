"""Shared strict numeric validation; booleans and non-finite values are rejected."""

from math import isfinite


def number(name: str, value: float, *, minimum: float = 0.0, strict: bool = False) -> None:
    try:
        valid = not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be a finite number")
    if value < minimum or (strict and value == minimum):
        sign = ">" if strict else ">="
        raise ValueError(f"{name} must be {sign} {minimum}")


def fraction(name: str, value: float, *, positive: bool = False) -> None:
    number(name, value, strict=positive)
    if value > 1.0:
        raise ValueError(f"{name} must be <= 1")
