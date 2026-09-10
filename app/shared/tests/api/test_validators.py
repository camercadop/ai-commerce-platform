import pytest
from pydantic import BaseModel

from app.shared.api.validators import sanitize_strings


class _Schema(BaseModel):
    name: str
    value: object = None

    _strip = sanitize_strings("name")


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


def test_non_string_value_is_passed_through() -> None:
    assert _Schema(name="x", value=42).value == 42
