"""
BharatBuild CLI — Project Management
========================================
list_projects, open_project, delete_project, import_project,
show_project_files, download_project

All functions are async and accept a CLIConfig as first argument.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from cli.config import CLIConfig

console = Console()

# ── status → colour ──────────────────────────────────────────────────────────
_STATUS_COLOR = {
    "completed":   "green",
    "running":     "cyan",
    "failed":      "red",
    "pending":     "yellow",
    "generating":  "blue",
    "idle":        "dim",
}

# ── mode → icon ──────────────────────────────────────────────────────────────
_MODE_ICON = {
    "student":   "🎓",
    "developer": "💻",
    "founder":   "🚀",
    "college":   "🏫",
    "api":       "🔌",
}


# ── list ─────────────────────────────────────────────────────────────────────

async def list_projects(config: CLIConfig, limit: int = 20) -> None:
    """Print a rich table of the user's projects."""
    from cli.client import BharatBuildClient, APIError
    from cli.auth import AuthManager

    AuthManager.require()

    with console.status("[cyan]Loading projects…[/cyan]", spinner="dots"):
        try:
            async with BharatBuildClient(config) as client:
                data = await client.list_projects(limit=limit)
        except APIError as exc:
            console.print(f"[red]✗ {exc.detail}[/red]")
            return

    projects = data if isinstance(data, list) else data.get("projects", data.get("items", []))

    if not projects:
        console.print(Panel(
            "[dim]No projects yet.\n\nRun [cyan]bharatbuild \"create a todo app\"[/cyan] "
            "to generate your first project.[/dim]",
            title="Projects",
            border_style="dim",
        ))
        return

    t = Table(
        title=f"Your Projects  ({len(projects)})",
        border_style="cyan",
        header_style="bold cyan",
        show_lines=False,
    )
    t.add_column("#",       style="dim",          width=3,  justify="right")
    t.add_column("Title",   style="bold white",   min_width=24)
    t.add_column("Mode",    style="cyan",          width=12)
    t.add_column("Status",  width=14)
    t.add_column("ID",      style="dim",           width=10)
    t.add_column("Created", style="dim",           width=12)

    for i, p in enumerate(projects, 1):
        status = p.get("status", "idle")
        sc     = _STATUS_COLOR.get(status.lower(), "white")
        mode   = p.get("mode", "developer")
        icon   = _MODE_ICON.get(mode.lower(), "")
        pid    = str(p.get("id", ""))[:8]
        created = str(p.get("created_at", ""))[:10]
        t.add_row(
            str(i),
            p.get("title", "Untitled"),
            f"{icon} {mode}",
            Text(status, style=sc),
            pid,
            created,
        )

    console.print()
    console.print(t)
    console.print()
    console.print("[dim]Tip: use [cyan]/project <id>[/cyan] to switch to a project.[/dim]")
    console.print()


# ── detail view ──────────────────────────────────────────────────────────────

async def show_project(config: CLIConfig, project_id: str) -> None:
    """Print detailed info about a single project."""
    from cli.client import BharatBuildClient, APIError

    with console.status("[cyan]Loading project…[/cyan]", spinner="dots"):
        try:
            async with BharatBuildClient(config) as client:
                proj = await client.get_project(project_id)
        except APIError as exc:
            console.print(f"[red]✗ {exc.detail}[/red]")
            return

    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="dim",   justify="right")
    t.add_column(style="white bold")

    fields = [
        ("ID",          proj.get("id", "")),
        ("Title",       proj.get("title", "")),
        ("Mode",        proj.get("mode", "")),
        ("Status",      proj.get("status", "")),
        ("Description", proj.get("description", "")),
        ("Created",     str(proj.get("created_at", ""))[:19]),
        ("Updated",     str(proj.get("updated_at", ""))[:19]),
    ]
    for label, value in fields:
        if value:
            t.add_row(label, str(value))

    console.print(Panel(t, title=f"[cyan]{proj.get('title', project_id)}[/cyan]",
                        border_style="cyan"))


# ── file listing ──────────────────────────────────────────────────────────────

async def show_project_files(config: CLIConfig, project_id: str) -> None:
    """List files inside a project."""
    from cli.client import BharatBuildClient, APIError

    with console.status("[cyan]Listing files…[/cyan]", spinner="dots"):
        try:
            async with BharatBuildClient(config) as client:
                data = await client.get(f"/projects/{project_id}/files")
        except APIError as exc:
            console.print(f"[red]✗ {exc.detail}[/red]")
            return

    files = data if isinstance(data, list) else data.get("files", [])

    if not files:
        console.print("[dim]No files found.[/dim]")
        return

    t = Table(title="Project Files", border_style="dim",
              header_style="bold cyan", show_lines=False)
    t.add_column("Path",     style="white", min_width=30)
    t.add_column("Language", style="cyan",  width=14)
    t.add_column("Size",     style="dim",   width=10, justify="right")

    for f in files:
        size_bytes = f.get("size_bytes", 0)
        size_str   = (
            f"{size_bytes // 1024} KB" if size_bytes >= 1024
            else f"{size_bytes} B"
        )
        t.add_row(
            f.get("path", ""),
            f.get("language", ""),
            size_str,
        )

    console.print(t)


# ── delete ────────────────────────────────────────────────────────────────────

async def delete_project(config: CLIConfig, project_id: str, force: bool = False) -> None:
    """Delete a project after confirmation."""
    from cli.client import BharatBuildClient, APIError

    if not force:
        confirmed = Confirm.ask(
            f"[red]Delete project [bold]{project_id}[/bold]? This cannot be undone.[/red]"
        )
        if not confirmed:
            console.print("[dim]Cancelled.[/dim]")
            return

    with console.status("[red]Deleting…[/red]", spinner="dots"):
        try:
            async with BharatBuildClient(config) as client:
                await client.delete_project(project_id)
        except APIError as exc:
            console.print(f"[red]✗ {exc.detail}[/red]")
            return

    console.print(f"[green]✓ Project {project_id} deleted.[/green]")


# ── download / export ────────────────────────────────────────────────────────

async def download_project(config: CLIConfig, project_id: str, dest: Optional[Path] = None) -> None:
    """Download a project ZIP and extract it locally."""
    from cli.client import BharatBuildClient, APIError
    import httpx

    dest = dest or Path(".") / project_id
    dest.mkdir(parents=True, exist_ok=True)

    with console.status("[cyan]Downloading project…[/cyan]", spinner="dots"):
        try:
            async with BharatBuildClient(config) as client:
                # hit the download endpoint — returns a zip stream
                resp = await client._request("GET", f"/download/{project_id}/zip")
        except APIError as exc:
            console.print(f"[red]✗ {exc.detail}[/red]")
            return

    zip_path = dest / f"{project_id}.zip"
    zip_path.write_bytes(resp.content)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)
    zip_path.unlink()

    console.print(f"[green]✓ Project extracted to [bold]{dest.resolve()}[/bold][/green]")


# ── import ────────────────────────────────────────────────────────────────────

async def import_project(config: CLIConfig, path: Path) -> None:
    """
    Upload a local folder (or zip) to BharatBuild for AI analysis and import.
    """
    from cli.client import BharatBuildClient, APIError

    if not path.exists():
        console.print(f"[red]✗ Path not found: {path}[/red]")
        return

    # zip the folder if it's a directory
    if path.is_dir():
        import tempfile
        with console.status("[cyan]Zipping project…[/cyan]", spinner="dots"):
            tmp = Path(tempfile.mktemp(suffix=".zip"))
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
                for fp in sorted(path.rglob("*")):
                    if fp.is_file() and ".git" not in fp.parts:
                        zf.write(fp, fp.relative_to(path))
        upload_path = tmp
        cleanup = True
    else:
        upload_path = path
        cleanup = False

    title = Prompt.ask("  [cyan]Project title[/cyan]", default=path.name)

    with console.status("[cyan]Uploading and analysing…[/cyan]", spinner="dots"):
        try:
            async with BharatBuildClient(config) as client:
                resp = await client.upload(
                    "/import/upload",
                    upload_path,
                    field="file",
                )
        except APIError as exc:
            console.print(f"[red]✗ Upload failed: {exc.detail}[/red]")
            if cleanup:
                upload_path.unlink(missing_ok=True)
            return

    if cleanup:
        upload_path.unlink(missing_ok=True)

    pid = resp.get("project_id", "")
    console.print(f"[green]✓ Imported![/green]  Project ID: [bold]{pid}[/bold]")
    if pid:
        console.print(f"[dim]Use [cyan]/project {pid}[/cyan] to switch to it.[/dim]")
