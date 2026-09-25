"""Reusable field validators."""


def validate_password_strength(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 bytes.")
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
        raise ValueError("Password must contain at least one letter and one number.")
    return value


def clean_text(value: str) -> str:
    return value.strip()
