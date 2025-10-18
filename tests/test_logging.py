from __future__ import annotations

import logging
from io import StringIO

from repo_radar.logging import SecretFilter, mask_secrets, setup_logging


def test_mask_secrets_github_token():
    original = "Token ghp_abcdefghijklmnopqrstuvwxyz1234"
    masked = mask_secrets(original)
    # Ensure token body is masked but prefix remains
    assert "ghp_" in masked
    assert masked != original
    # Should contain *** indicating masking
    assert "***" in masked


def test_mask_secrets_bearer_header():
    original = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123456789"
    masked = mask_secrets(original)
    assert masked.startswith("Authorization: Bearer ")
    assert "***" in masked
    assert masked != original


def test_secret_filter_applies_to_logs():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(SecretFilter())
    logger = logging.getLogger("repo_radar.test")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    logger.info("smtp_pass=%s", "supersecretpassword")
    handler.flush()

    out = stream.getvalue()
    assert "supersecretpassword" not in out
    assert "***" in out


def test_setup_logging_adds_filter_and_handler(monkeypatch):
    # Remove handlers to simulate fresh environment
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    logger = setup_logging(level="INFO")
    assert logger is logging.getLogger("repo_radar")

    # Root should have at least one handler and SecretFilter attached
    assert root.handlers
    assert any(any(isinstance(f, SecretFilter) for f in h.filters) for h in root.handlers)
