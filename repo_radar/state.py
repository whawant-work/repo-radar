from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

STATE_DEFAULT_PATH = Path("config/.state/last_run.txt")


def now_iso() -> str:
    """Return current UTC time in RFC3339 format without microseconds.

    Example: 2025-10-12T05:00:00Z
    """
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_last_run(path: Path | None = None) -> str | None:
    """Read last run ISO timestamp from file. Returns None if file missing or empty."""
    p = path or STATE_DEFAULT_PATH
    if not p.exists():
        return None
    try:
        content = p.read_text(encoding="utf-8").strip()
        return content or None
    except Exception:
        # On any read error, treat as no state
        return None


def set_last_run(when_iso: str | None = None, path: Path | None = None) -> None:
    """Write last run ISO timestamp to file. Creates directories as needed.

    If when_iso is None, writes current UTC time.
    """
    p = path or STATE_DEFAULT_PATH
    ensure_parent(p)
    ts = when_iso or now_iso()
    p.write_text(ts + "\n", encoding="utf-8")


__all__ = [
    "STATE_DEFAULT_PATH",
    "now_iso",
    "get_last_run",
    "set_last_run",
]
