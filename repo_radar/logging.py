from __future__ import annotations

import logging
import re
import sys

SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # GitHub classic/fine-grained tokens often start with ghp_/gho_/ghu_/ghs_/ghr_
    # Keep first 4 and last 4 characters, mask the middle.
    (re.compile(r"(?P<prefix>gh[pousr]_)(?P<body>[A-Za-z0-9_\-]{16,})"), r"\g<prefix>\g<body>"),
    # Bearer tokens in Authorization headers
    (
        re.compile(r"(?i)(Authorization\s*:\s*Bearer\s+)(?P<tok>[A-Za-z0-9._\-~+=/]{12,})"),
        r"\1\g<tok>",
    ),
    # Generic token/password style key=value pairs
    (
        re.compile(r"(?i)(token|api[_-]?key|secret|password|pass|smtp_pass)\s*[:=]\s*([^\s,;]+)"),
        r"\1=\2",
    ),
]


def _mask_chunk(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}***{value[-4:]}"


def mask_secrets(text: str) -> str:
    """Mask likely secrets in the given text.

    Heuristics:
    - gh[pousr]_... GitHub tokens -> keep first/last 4 chars
    - Authorization: Bearer <token> -> mask token body
    - key=value for token/password-like keys -> mask value
    """
    if not text:
        return text

    # Mask GitHub tokens first
    def repl_github(m: re.Match[str]) -> str:
        prefix = m.group("prefix")
        body = m.group("body")
        return prefix + _mask_chunk(body)

    text = re.sub(SECRET_PATTERNS[0][0], repl_github, text)

    # Mask Bearer tokens
    def repl_bearer(m: re.Match[str]) -> str:
        head = m.group(1)
        tok = m.group("tok")
        return f"{head}{_mask_chunk(tok)}"

    text = re.sub(SECRET_PATTERNS[1][0], repl_bearer, text)

    # Mask generic key=value secrets
    def repl_kv(m: re.Match[str]) -> str:
        key = m.group(1)
        return f"{key}={_mask_chunk(m.group(2))}"

    text = re.sub(SECRET_PATTERNS[2][0], repl_kv, text)

    return text


class SecretFilter(logging.Filter):
    """Logging filter that masks secrets in log messages.

    It rewrites record.msg into a fully rendered, masked string and clears args
    to avoid double formatting downstream.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        try:
            rendered = record.getMessage()
            masked = mask_secrets(str(rendered))
            record.msg = masked
            record.args = None  # type: ignore[assignment]
        except Exception:
            # Best-effort; never break logging
            pass
        return True


def setup_logging(level: int | str = "INFO") -> logging.Logger:
    """Initialize repo-radar logging with secret-masking filter.

    - Sets root level to the provided level (string or int)
    - Adds a StreamHandler to stderr if none exists
    - Applies SecretFilter to all repo_radar handlers
    - Returns the package logger ("repo_radar")
    """
    if isinstance(level, str):
        level = logging._nameToLevel.get(level.upper(), logging.INFO)  # type: ignore[attr-defined]

    root = logging.getLogger()
    root.setLevel(level)  # ensure we don't drop messages

    # Ensure at least one handler exists on root
    if not root.handlers:
        handler = logging.StreamHandler(stream=sys.stderr)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
        handler.setFormatter(fmt)
        root.addHandler(handler)

    # Attach SecretFilter to all existing handlers
    for h in root.handlers:
        # Avoid adding duplicates
        if not any(isinstance(f, SecretFilter) for f in getattr(h, "filters", [])):
            h.addFilter(SecretFilter())

    # Package logger convenience
    pkg_logger = logging.getLogger("repo_radar")
    pkg_logger.propagate = True
    pkg_logger.setLevel(level)
    return pkg_logger


__all__ = ["setup_logging", "SecretFilter", "mask_secrets"]
