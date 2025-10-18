from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from repo_radar import __version__, load_config
from repo_radar.github_client import GitHubAPIError, GitHubClient
from repo_radar.logging import setup_logging
from repo_radar.registry import RepoRegistryError, load_repos, validate_repos

logger = logging.getLogger(__name__)


def cmd_config(args: argparse.Namespace) -> int:
    """Display current configuration with repository validation.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    cfg = load_config()
    redacted = cfg.redacted_dict()

    # Optional connectivity check
    if args.check_github:
        if "/" not in args.check_github:
            print("\n❌ Invalid format for --check-github. Use OWNER/REPO.")
            return 2
        owner, repo = args.check_github.split("/", 1)
        client = GitHubClient(token=cfg.github.token)
        try:
            info = client.get_repo(owner, repo)
        except GitHubAPIError as exc:
            print(f"\n❌ GitHub check failed: {exc}")
            return 3
        else:
            print("\n✅ GitHub connectivity OK")
            # Show minimal fields to avoid noise
            minimal = {k: info.get(k) for k in ("full_name", "private", "default_branch")}
            print(json.dumps(minimal, indent=2, ensure_ascii=False))

    print(f"🔧 repo-radar Configuration (v{__version__})")
    print("=" * 50)
    print(json.dumps(redacted, indent=2, ensure_ascii=False))

    # Repository registry check
    registry_path = Path(args.repos) if args.repos else Path("config/repos.list")
    if not registry_path.exists():
        print(f"\nℹ️  Repository registry not found: {registry_path}")
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
            return 1

    # Additional configuration checks
    issues = []
    if cfg.email.email_to and not cfg.email.email_from:
        issues.append("⚠️  EMAIL_FROM required when EMAIL_TO is set")

    if issues:
        print("\n⚠️  Configuration Issues:")
        for issue in issues:
            print(f"   {issue}")

    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run full digest pipeline: collect → classify → render → publish → notify.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger.info("Starting full digest pipeline")
    logger.info(f"Repos file: {args.repos}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Email enabled: {not args.no_email}")

    print("🚧 Full pipeline execution is not yet implemented")
    print("\nPlanned steps:")
    print("  1. Collect PRs/Issues from GitHub (collector.py)")
    print("  2. Classify items by rules (rules.py - not yet implemented)")
    print("  3. Build digest with KPIs (digest.py - not yet implemented)")
    print("  4. Render HTML/JSON output (renderer.py - not yet implemented)")
    print("  5. Publish to GitHub Pages (publisher.py - not yet implemented)")
    print("  6. Send email notification (notifier.py - not yet implemented)")
    print("\nThis feature will be available in future versions.")
    print("For now, you can use 'config' subcommand to check configuration.")

    return 0


def cmd_render_only(args: argparse.Namespace) -> int:
    """Render digest from existing collected data (skip collection).

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger.info("Starting render-only mode")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Email enabled: {not args.no_email}")

    print("🚧 Render-only mode is not yet implemented")
    print("\nPlanned steps:")
    print("  1. Load existing collected data from state")
    print("  2. Classify items by rules (rules.py - not yet implemented)")
    print("  3. Build digest with KPIs (digest.py - not yet implemented)")
    print("  4. Render HTML/JSON output (renderer.py - not yet implemented)")
    print("  5. Optionally publish and notify")
    print("\nThis feature will be available in future versions.")

    return 0


def main() -> None:
    """CLI entry point with subcommand support.

    WBS 9.1 Day2 - CLI Entry (Draft): ✅ COMPLETED

    ✅ Successfully implemented CLI entry with:
    - argparse-based subcommand structure (standard library)
    - Three subcommands: config, run, render-only
    - Common options: --repos, --output, --no-email, --log-level
    - Backward compatibility maintained (config is default)
    - Help/usage messages for all commands
    - Placeholder implementations for future features

    Usage examples:
    - uv run python main.py config              # Show configuration
    - uv run python main.py run                 # Run full pipeline (future)
    - uv run python main.py render-only         # Render only (future)
    - uv run python main.py --help              # Show help
    """
    # Initialize logging early (default INFO). Users can override via --log-level.
    setup_logging(level=os.environ.get("LOG_LEVEL", "INFO"))

    parser = argparse.ArgumentParser(
        prog="repo-radar",
        description="Daily digest of your GitHub universe — PRs, issues, and reviews",
        epilog=f"repo-radar version {__version__}",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"repo-radar {__version__}",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=os.environ.get("LOG_LEVEL", "INFO"),
        help="Set logging level (default: INFO)",
    )

    subparsers = parser.add_subparsers(
        title="subcommands",
        description="Available commands",
        dest="command",
        help="Use '<command> --help' for more information",
    )

    # Subcommand: config (default behavior)
    parser_config = subparsers.add_parser(
        "config",
        help="Display current configuration and validate setup",
        description="Show configuration with sensitive values masked and "
        "validate repository registry",
    )
    parser_config.add_argument(
        "--repos",
        metavar="FILE",
        help="Repository list file path (default: config/repos.list)",
    )
    parser_config.add_argument(
        "--check-github",
        metavar="OWNER/REPO",
        help="Verify GitHub API connectivity by fetching repository info",
    )
    parser_config.set_defaults(func=cmd_config)

    # Subcommand: run
    parser_run = subparsers.add_parser(
        "run",
        help="Run full digest pipeline (collect → classify → render → publish → notify)",
        description="Execute complete workflow: collect PRs/Issues, classify by rules, "
        "render digest, publish to GitHub Pages, and send email notification",
    )
    parser_run.add_argument(
        "--repos",
        metavar="FILE",
        default="config/repos.list",
        help="Repository list file path (default: config/repos.list)",
    )
    parser_run.add_argument(
        "--output",
        metavar="DIR",
        default="output",
        help="Output directory for generated files (default: output/)",
    )
    parser_run.add_argument(
        "--no-email",
        action="store_true",
        help="Skip email notification",
    )
    parser_run.set_defaults(func=cmd_run)

    # Subcommand: render-only
    parser_render = subparsers.add_parser(
        "render-only",
        help="Render digest from existing data (skip collection)",
        description="Generate digest from previously collected data "
        "without re-fetching from GitHub",
    )
    parser_render.add_argument(
        "--output",
        metavar="DIR",
        default="output",
        help="Output directory for generated files (default: output/)",
    )
    parser_render.add_argument(
        "--no-email",
        action="store_true",
        help="Skip email notification",
    )
    parser_render.set_defaults(func=cmd_render_only)

    args = parser.parse_args()

    # Update log level if specified
    if args.log_level:
        setup_logging(level=args.log_level)

    # If no subcommand specified, default to config for backward compatibility
    if not args.command:
        args.command = "config"
        args.func = cmd_config
        args.repos = None
        args.check_github = None

    # Execute subcommand
    try:
        exit_code = args.func(args)
        sys.exit(exit_code)
    except Exception as exc:
        logger.exception("Unexpected error occurred")
        print(f"\n❌ Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
