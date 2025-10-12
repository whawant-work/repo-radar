from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


class RepoRadarConfigError(ValueError):
    """Raised when configuration is invalid or cannot be loaded."""


def _env(key: str, default: str | None = None) -> str | None:
    # Support both plain names and prefixed variants for flexibility
    candidates = [key, f"REPORADAR_{key}", f"REPO_RADAR_{key}"]
    for name in candidates:
        if name in os.environ:
            return os.environ[name]
    return default


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _is_owner_repo(s: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", s))


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}***{value[-4:]}"


@dataclass
class GithubAuth:
    token: str | None = None  # PAT (optional for public-only)

    def redacted(self) -> GithubAuth:
        return GithubAuth(token=_mask_secret(self.token))


@dataclass
class EmailConfig:
    provider: str = "smtp"  # smtp|ses|sendgrid (MVP: smtp)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_pass: str | None = None
    email_from: str | None = None
    email_to: list[str] = field(default_factory=list)

    def redacted(self) -> EmailConfig:
        c = asdict(self)
        c["smtp_pass"] = _mask_secret(self.smtp_pass)
        return EmailConfig(**c)


@dataclass
class GhPagesConfig:
    repo: str | None = None  # you/repo-radar-pages
    branch: str = "gh-pages"
    base_url: str | None = None


@dataclass
class LoadOptions:
    # .env support
    load_dotenv: bool = True
    dotenv_path: str | Path | None = None
    dotenv_override: bool = False  # if True, overrides existing os.environ


@dataclass
class Config:
    timezone: str = "UTC"
    daily_at: str = "09:00"  # HH:MM 24h
    repos: list[str] = field(default_factory=list)
    rules_file: str | None = None
    quiet_hours: tuple[str, str] | None = None  # (start, end) HH:MM

    github: GithubAuth = field(default_factory=GithubAuth)
    email: EmailConfig = field(default_factory=EmailConfig)
    pages: GhPagesConfig = field(default_factory=GhPagesConfig)

    @property
    def repos_owner_repo(self) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for r in self.repos:
            owner, name = r.split("/", 1)
            pairs.append((owner, name))
        return pairs

    def redacted_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["github"]["token"] = _mask_secret(self.github.token)
        d["email"]["smtp_pass"] = _mask_secret(self.email.smtp_pass)
        return d


def _from_env() -> dict[str, Any]:
    out: dict[str, Any] = {}
    # flat
    if tz := _env("TIMEZONE"):
        out["timezone"] = tz
    if da := _env("DAILY_AT"):
        out["daily_at"] = da
    repos_env = _env("REPOS")
    if repos_env:
        out["repos"] = _split_csv(repos_env)
    if rf := _env("RULES_FILE"):
        out["rules_file"] = rf
    # quiet hours as HH:MM-HH:MM
    if (qh := _env("QUIET_HOURS")) and "-" in qh:
        s, e = (x.strip() for x in qh.split("-", 1))
        out["quiet_hours"] = (s, e)

    # github
    gh: dict[str, Any] = {}
    if tok := _env("GITHUB_TOKEN"):
        gh["token"] = tok
    if gh:
        out["github"] = gh

    # email
    email: dict[str, Any] = {}
    if prov := _env("EMAIL_PROVIDER"):
        email["provider"] = prov
    if h := _env("EMAIL_SMTP_HOST"):
        email["smtp_host"] = h
    if p := _env("EMAIL_SMTP_PORT"):
        try:
            email["smtp_port"] = int(p)
        except ValueError as exc:
            raise RepoRadarConfigError("EMAIL_SMTP_PORT must be an integer") from exc
    if u := _env("EMAIL_SMTP_USER"):
        email["smtp_user"] = u
    if pw := _env("EMAIL_SMTP_PASS"):
        email["smtp_pass"] = pw
    if frm := _env("EMAIL_FROM"):
        email["email_from"] = frm
    if to := _env("EMAIL_TO"):
        email["email_to"] = _split_csv(to)
    if email:
        out["email"] = email

    # pages
    pages: dict[str, Any] = {}
    if pr := _env("GH_PAGES_REPO"):
        pages["repo"] = pr
    if pb := _env("GH_PAGES_BRANCH"):
        pages["branch"] = pb
    if bu := _env("BASE_URL"):
        pages["base_url"] = bu
    if pages:
        out["pages"] = pages

    return out


_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def _validate(cfg: Config) -> None:
    # timezone
    try:
        ZoneInfo(cfg.timezone)
    except Exception as exc:
        raise RepoRadarConfigError(f"Invalid TIMEZONE: {cfg.timezone}") from exc

    # time formats
    if not _TIME_RE.fullmatch(cfg.daily_at):
        raise RepoRadarConfigError("DAILY_AT must be HH:MM (24h)")
    if cfg.quiet_hours is not None:
        s, e = cfg.quiet_hours
        if not (_TIME_RE.fullmatch(s) and _TIME_RE.fullmatch(e)):
            raise RepoRadarConfigError("QUIET_HOURS must be 'HH:MM-HH:MM'")

    # repos
    for r in cfg.repos:
        if not _is_owner_repo(r):
            raise RepoRadarConfigError(f"Invalid repo '{r}', expected 'owner/name'")

    # email basic checks when SMTP is intended
    if cfg.email.provider == "smtp":
        if cfg.email.email_to and not cfg.email.email_from:
            raise RepoRadarConfigError("EMAIL_FROM is required when EMAIL_TO is set")

    # pages
    if cfg.pages.base_url and not cfg.pages.base_url.startswith("http"):
        raise RepoRadarConfigError("BASE_URL must start with http/https")


def load_config(options: LoadOptions | None = None) -> Config:
    """Load configuration with precedence: env > .env > defaults.

    WBS 2.1 Day1 Implementation: ✅ COMPLETED
    - ✅ Environment variable loading with flexible key support (REPORADAR_*/REPO_RADAR_* prefixes)
    - ✅ .env file loading with python-dotenv integration
    - ✅ Proper precedence: OS env > .env file > defaults
    - ✅ Comprehensive validation (timezone, time format, repo format, email requirements)
    - ✅ Secret masking for sensitive values (tokens, passwords)
    - ✅ Structured configuration with dataclasses (Config, GithubAuth, EmailConfig, etc.)
    - ✅ Flexible .env path options (auto-search ./.env, ./config/.env or custom path)
    - ✅ Override control for .env vs OS environment variables

    Args:
        options: LoadOptions with .env loading preferences (load_dotenv, dotenv_path,
                dotenv_override)

    Returns:
        Config: Validated configuration object with masked secrets in redacted output

    Raises:
        RepoRadarConfigError: When configuration validation fails
    """
    options = options or LoadOptions()

    # Load .env file if enabled
    if options.load_dotenv:
        try:
            from dotenv import load_dotenv

            dotenv_path = options.dotenv_path
            if dotenv_path is None:
                # Default search: ./.env, ./config/.env
                for candidate in (Path(".env"), Path("config/.env")):
                    if candidate.exists():
                        dotenv_path = candidate
                        break
            if dotenv_path is not None:
                load_dotenv(dotenv_path, override=options.dotenv_override)
            else:
                # Auto-search in current directory
                load_dotenv(override=options.dotenv_override)
        except Exception:
            # Ignore missing dotenv or file errors - .env is optional
            pass

    # Load from environment variables (.env already loaded above)
    env_data = _from_env()

    # Construct dataclasses
    cfg = Config(
        timezone=env_data.get("timezone", Config.timezone),
        daily_at=env_data.get("daily_at", Config.daily_at),
        repos=list(env_data.get("repos", []) or []),
        rules_file=env_data.get("rules_file"),
        quiet_hours=tuple(env_data.get("quiet_hours")) if env_data.get("quiet_hours") else None,  # type: ignore[arg-type]
        github=GithubAuth(**env_data.get("github", {})),
        email=EmailConfig(**env_data.get("email", {})),
        pages=GhPagesConfig(**env_data.get("pages", {})),
    )

    _validate(cfg)
    return cfg
