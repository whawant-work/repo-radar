from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root is importable for tests (so `import repo_radar` works without install)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Clear keys that may be populated by previous load_dotenv calls to avoid test leakage
    keys = [
        "TIMEZONE",
        "DAILY_AT",
        "REPOS",
        "RULES_FILE",
        "QUIET_HOURS",
        "GITHUB_TOKEN",
        "EMAIL_PROVIDER",
        "EMAIL_SMTP_HOST",
        "EMAIL_SMTP_PORT",
        "EMAIL_SMTP_USER",
        "EMAIL_SMTP_PASS",
        "EMAIL_FROM",
        "EMAIL_TO",
        "GH_PAGES_REPO",
        "GH_PAGES_BRANCH",
        "BASE_URL",
    ]
    for k in keys:
        monkeypatch.delenv(k, raising=False)
