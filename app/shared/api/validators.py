from typing import Any

from pydantic import field_validator


def sanitize_strings(*fields: str) -> Any:
    """Return a Pydantic field validator that strips control characters from strings.

    Strips newline and carriage return characters to prevent log injection.
    Assign the result to a `_strip` class attribute in any Pydantic schema.

    Args:
        *fields: The field names to sanitize.

    Example:
        class MyRequest(BaseModel):
            name: str
            email: str

            _strip = sanitize_strings("name", "email")
    """

    @field_validator(*fields, mode="before")  # type: ignore[misc]
    @classmethod
    def _strip_control_characters(cls: type[Any], v: object) -> object:
        if isinstance(v, str):
            return v.replace("\n", "").replace("\r", "")
        return v

    return _strip_control_characters
