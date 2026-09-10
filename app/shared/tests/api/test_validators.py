import pytest
from pydantic import BaseModel

from app.shared.api.validators import sanitize_strings


class _Schema(BaseModel):
    name: str

    _strip = sanitize_strings("name")


class _SchemaWithNonString(BaseModel):
    value: object

    _strip = sanitize_strings("value")


def test_sanitizes_strings(subtests: pytest.Subtests) -> None:
    cases = [
        ("strips newline", "foo\nbar", "foobar"),
        ("strips carriage return", "foo\rbar", "foobar"),
        ("strips both control characters", "foo\r\nbar", "foobar"),
        ("clean string is unchanged", "foobar", "foobar"),
    ]
    for description, value, expected in cases:
        with subtests.test(description):
            assert _Schema(name=value).name == expected


def test_non_string_value_is_passed_through(subtests: pytest.Subtests) -> None:
    cases = [
        ("integer", 42),
        ("none", None),
        ("list", [1, 2, 3]),
    ]
    for description, value in cases:
        with subtests.test(description):
            assert _SchemaWithNonString(value=value).value == value
