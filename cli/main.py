#!/usr/bin/env python3
"""
BharatBuild CLI - Entry Point

Usage:
    bharatbuild                          Interactive REPL
    bharatbuild "create a todo app"      Single-shot generation
    bharatbuild login                    Authenticate
    bharatbuild logout                   Clear credentials
    bharatbuild register                 Create account
    bharatbuild whoami                   Show account info
    bharatbuild projects                 List projects
    bharatbuild doctor                   Run diagnostics
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bharatbuild",
        description="BharatBuild AI - AI-powered code generation for India",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bharatbuild                             Start interactive REPL
  bharatbuild login                       Login to your account
  bharatbuild register                    Create a new account
  bharatbuild "create a React todo app"   Generate a project
  bharatbuild -p "add dark mode"          Run a single prompt
  bharatbuild projects                    List your projects
  bharatbuild doctor                      Diagnose environment
        """,
    )

    parser.add_argument("prompt", nargs="?", default=None,
                        help="Prompt to send (single-shot mode)")
    parser.add_argument("-p", "--prompt-flag", dest="prompt_flag",
                        metavar="PROMPT", help="Prompt (flag form)")
    parser.add_argument("-m", "--model", default=None,
                        choices=["haiku", "sonnet", "opus"])
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--mode", default=None, choices=["ask", "auto", "deny"])
    parser.add_argument("-n", "--non-interactive", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--version", action="version", version="bharatbuild 1.0.0")

    sub = parser.add_subparsers(dest="command")

    login_p = sub.add_parser("login", help="Login to BharatBuild")
    login_p.add_argument("--token", "-t", metavar="TOKEN",
                         help="CLI token from web portal")

    sub.add_parser("logout",   help="Clear stored credentials")
    sub.add_parser("register", help="Create a new account")
    sub.add_parser("whoami",   help="Show logged-in account details")

    proj_p = sub.add_parser("projects", help="List your projects")
    proj_p.add_argument("--limit", type=int, default=20)

    doc_p = sub.add_parser("doctor", help="Run environment diagnostics")

    del_p = sub.add_parser("delete", help="Delete a project")
    del_p.add_argument("project_id", help="Project ID to delete")
    del_p.add_argument("--force", "-f", action="store_true")

    dl_p = sub.add_parser("download", help="Download a project as ZIP")
    dl_p.add_argument("project_id")
    dl_p.add_argument("--dest", "-d", default=None)

    return parser


async def _async_main() -> None:
    from cli.config import CLIConfig
    from cli.auth import AuthManager, interactive_login, interactive_register, login_with_token, print_whoami

    parser = _build_parser()
    args   = parser.parse_args()

    # ── load config & apply CLI overrides ────────────────────────────────────
    config = CLIConfig.load_default()

    if args.model:
        config.model = args.model
    if args.api_url:
        config.api_base_url = args.api_url
    if args.api_key:
        config.api_key = args.api_key
    if args.mode:
        config.permission_mode = args.mode
    if args.non_interactive:
        config.non_interactive = True
    if args.verbose:
        config.verbose = True

    # inject stored credentials into config
    creds = AuthManager.load()
    if creds:
        AuthManager.inject_into_config(config, creds)

    # ── sub-command dispatch ──────────────────────────────────────────────────
    cmd = args.command

    if cmd == "login":
        token = getattr(args, "token", None)
        if token:
            await login_with_token(config, token)
        else:
            await interactive_login(config)
        return

    if cmd == "logout":
        AuthManager.logout()
        from rich.console import Console
        Console().print("[green]Logged out.[/green]")
        return

    if cmd == "register":
        await interactive_register(config)
        return

    if cmd == "whoami":
        creds = AuthManager.require()
        print_whoami(creds)
        return

    if cmd == "projects":
        from cli.projects import list_projects
        await list_projects(config, limit=args.limit)
        return

    if cmd == "doctor":
        from cli.doctor import run_doctor
        await run_doctor(config)
        return

    if cmd == "delete":
        from cli.projects import delete_project
        await delete_project(config, args.project_id, force=args.force)
        return

    if cmd == "download":
        from cli.projects import download_project
        dest = Path(args.dest) if args.dest else None
        await download_project(config, args.project_id, dest=dest)
        return

    # ── resolve prompt (positional or flag) ───────────────────────────────────
    prompt = args.prompt or args.prompt_flag

    # ── single-shot mode ──────────────────────────────────────────────────────
    if prompt:
        from cli.app import BharatBuildCLI
        app = BharatBuildCLI(config)
        await app.run_once(prompt)
        return

    # ── interactive REPL ──────────────────────────────────────────────────────
    from cli.app import BharatBuildCLI
    app = BharatBuildCLI(config)
    await app.run()


def main() -> None:
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        print("\nBye!")
    except Exception as exc:
        from rich.console import Console
        Console().print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
