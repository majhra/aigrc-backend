"""
Simple validation utilities to avoid circular imports.
"""
import re
from app.core.config import settings


def validate_password(password: str) -> str:
    """
    Validate the password.
    :param password: The password to validate.
    :return: The validated password.
    """
    assert (
        len(password) >= settings.MIN_PASSWORD_LENGTH
    ), f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long"

    assert re.search(
        r"[a-z]", password
    ), "Password must contain at least 1 lowercase letter"

    assert re.search(
        r"[A-Z]", password
    ), "Password must contain at least 1 uppercase letter"

    assert re.search(r"[0-9]", password), "Password must contain at least 1 number"

    assert re.search(
        r"[!@#$%^&*()\-+={}[\]:;\"'<>,.?/|\\~`]", password
    ), "Password must contain at least 1 special character"

    return password


def format_email(email: str) -> str:
    """
    Format the email address to be lowercase and stripped.
    :param email: The email address to format.
    :return: The formatted email address.
    """
    return email.lower().strip()