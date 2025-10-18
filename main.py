from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from repo_radar import __version__, load_config
from repo_radar.github_client import GitHubAPIError, GitHubClient
from repo_radar.logging import setup_logging
from repo_radar.registry import RepoRegistryError, load_repos, validate_repos


def main() -> None:
    """Load and display current configuration with sensitive values masked.

    WBS 2.1 Day1 - Configuration Loader Implementation: ✅ COMPLETED

    ✅ Successfully implemented env+config loader with:
    - Environment variable loading (TIMEZONE, DAILY_AT, GITHUB_TOKEN, etc.)
    - .env file support with python-dotenv integration
    - Proper precedence: OS env > .env > defaults
    - Comprehensive validation and error reporting
    - Secret masking for sensitive data (GITHUB_TOKEN, EMAIL_SMTP_PASS)
    - User-friendly configuration display with issue detection
    - Structured data classes for type safety and maintainability

    Usage examples:
    - cp .env.sample .env  # Configure via .env file
    - uv run python main.py  # View current configuration
    - uv run python main.py --generate  # Generate digest (future feature)
    """
    # Initialize logging early (default INFO). Users can override via env LOG_LEVEL.
    setup_logging(level=os.environ.get("LOG_LEVEL", "INFO"))

    parser = argparse.ArgumentParser(
        description="repo-radar GitHub digest tool",
        epilog=f"repo-radar version {__version__}",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"repo-radar {__version__}",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate digest (not implemented yet - shows placeholder message)",
    )
    parser.add_argument(
        "--check-github",
        metavar="OWNER/REPO",
        help="Quickly check GitHub API connectivity by fetching repo info",
    )
    args = parser.parse_args()

    if args.generate:
        print("🚧 Digest generation is not yet implemented")
        print("This feature will be available in future versions.")
        print("For now, you can only view the current configuration.")
        print("\nTo proceed with configuration check, run without --generate flag.")
        sys.exit(1)

    cfg = load_config()
    redacted = cfg.redacted_dict()

    # Optional connectivity check to satisfy Issue #6 acceptance
    if args.check_github:
        if "/" not in args.check_github:
            print("\n❌ Invalid format for --check-github. Use OWNER/REPO.")
            sys.exit(2)
        owner, repo = args.check_github.split("/", 1)
        client = GitHubClient(token=cfg.github.token)
        try:
            info = client.get_repo(owner, repo)
        except GitHubAPIError as exc:
            print(f"\n❌ GitHub check failed: {exc}")
            sys.exit(3)
        else:
            print("\n✅ GitHub connectivity OK")
            # Show minimal fields to avoid noise
            minimal = {k: info.get(k) for k in ("full_name", "private", "default_branch")}
            print(json.dumps(minimal, indent=2, ensure_ascii=False))
            # Continue to config display below

    print(f"🔧 repo-radar Configuration (v{__version__})")
    print("=" * 50)
    print(json.dumps(redacted, indent=2, ensure_ascii=False))

    # Quick guidance for repository registry (file-based)
    registry_path = Path("config/repos.list")
    if not registry_path.exists():
        print("\nℹ️  Repository registry not found: config/repos.list")
        print("   Create it from sample:")
        print("   cp config/repos.sample.list config/repos.list && edit config/repos.list")
    else:
        try:
            repos = load_repos(registry_path)
            print(f"\n📚 Loaded {len(repos)} repositories from {registry_path}")
            # Optional online validation when token is provided
            if cfg.github.token:
                errors = validate_repos(repos, cfg.github.token)
                if errors:
                    print("⚠️  Repository validation issues:")
                    for r, reason in sorted(errors.items()):
                        print(f"   - {r}: {reason}")
                else:
                    print("✅ All repositories are accessible (token validated)")
            else:
                print("ℹ️  Set GITHUB_TOKEN to validate repo existence/permissions")
        except RepoRegistryError as exc:
            print(f"\n❌ Failed to load registry: {exc}")
            sys.exit(1)

    # Additional configuration checks
    issues = []
    if cfg.email.email_to and not cfg.email.email_from:
        issues.append("⚠️  EMAIL_FROM required when EMAIL_TO is set")

    if issues:
        print("\n⚠️  Configuration Issues:")
        for issue in issues:
            print(f"   {issue}")


if __name__ == "__main__":
    main()
