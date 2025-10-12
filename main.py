from __future__ import annotations

import json

from repo_radar import load_config


def main() -> None:
    """Load and display current configuration with sensitive values masked.

    WBS 2.1 Day1 - Configuration Loader Implementation: ✅ COMPLETED

    ✅ Successfully implemented env+config loader with:
    - Environment variable loading (TIMEZONE, DAILY_AT, REPOS, GITHUB_TOKEN, etc.)
    - .env file support with python-dotenv integration
    - Proper precedence: OS env > .env > defaults
    - Comprehensive validation and error reporting
    - Secret masking for sensitive data (GITHUB_TOKEN, EMAIL_SMTP_PASS)
    - User-friendly configuration display with issue detection
    - Structured data classes for type safety and maintainability

    Usage examples:
    - cp .env.sample .env  # Configure via .env file
    - export REPOS=owner/repo  # Configure via environment variables
    - uv run python main.py  # View current configuration
    """
    cfg = load_config()
    redacted = cfg.redacted_dict()

    print("🔧 repo-radar Configuration")
    print("=" * 50)
    print(json.dumps(redacted, indent=2, ensure_ascii=False))

    # Quick validation summary
    issues = []
    if not cfg.repos:
        issues.append("⚠️  No repositories configured (set REPOS)")
    if cfg.email.email_to and not cfg.email.email_from:
        issues.append("⚠️  EMAIL_FROM required when EMAIL_TO is set")

    if issues:
        print("\n⚠️  Configuration Issues:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print(f"\n✅ Configuration looks good! ({len(cfg.repos)} repos configured)")


if __name__ == "__main__":
    main()
