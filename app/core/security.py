"""Startup guards.

A misconfigured secret is not a warning, it is an open door: anyone who can
read the repository could mint a token for any user.
"""

import logging
import secrets

from app.core.config import Settings

logger = logging.getLogger(__name__)

PLACEHOLDER_SECRETS = {
    "change-me-in-production",
    "replace-with-a-long-random-secret",
    "secret",
    "changeme",
}
MIN_SECRET_LENGTH = 32


class InsecureConfiguration(RuntimeError):
    """Refuses a boot that would expose user accounts."""


def verify_secrets(settings: Settings) -> None:
    problems: list[str] = []
    secret = settings.jwt_secret or ""
    if secret.strip().lower() in PLACEHOLDER_SECRETS:
        problems.append(
            "JWT_SECRET is still the placeholder value. Generate one with "
            f"'python -c \"import secrets; print(secrets.token_urlsafe(48))\"'"
        )
    elif len(secret) < MIN_SECRET_LENGTH:
        problems.append(f"JWT_SECRET is shorter than {MIN_SECRET_LENGTH} characters")

    if not problems:
        return
    message = "; ".join(problems)
    if settings.app_env.lower() in {"production", "prod", "staging"}:
        raise InsecureConfiguration(message)
    logger.warning("insecure configuration: %s", message)


def suggest_secret() -> str:
    return secrets.token_urlsafe(48)
