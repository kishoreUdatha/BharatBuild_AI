"""
CLI Reconnection Handler - Handles network disconnection and resume

Features:
1. Detect connection loss during streaming
2. Auto-retry with exponential backoff
3. Save progress checkpoints locally
4. Resume interrupted workflows
5. Heartbeat to keep connection alive
"""

import asyncio
import json
import time
import httpx
from pathlib import Path
from typing import Optional, Dict, Any, Callable, AsyncGenerator
from dataclasses import dataclass, asdict
from enum import Enum
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from cli.config import CLIConfig


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class WorkflowCheckpoint:
    """Local checkpoint for interrupted workflow"""
    project_id: str
    workflow_type: str
    current_step: str
    completed_steps: list
    generated_files: list
    pending_files: list
    context: dict
    timestamp: float
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowCheckpoint":
        return cls(**data)


class ReconnectionHandler:
    """
    Handles network disconnection and automatic recovery for CLI.

    Usage:
        handler = ReconnectionHandler(config, console)

        async for event in handler.stream_with_retry(url, data):
            process(event)
    """

    def __init__(self, config: CLIConfig, console: Console):
        self.config = config
        self.console = console
        self.status = ConnectionStatus.CONNECTED
        self.retry_count = 0
        self.max_retries = 5
        self.base_delay = 1.0  # seconds
        self.max_delay = 30.0  # seconds
        self.heartbeat_interval = 30  # seconds
        self.checkpoint_dir = Path(config.config_dir) / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._current_checkpoint: Optional[WorkflowCheckpoint] = None

    def _get_checkpoint_path(self, project_id: str) -> Path:
        """Get checkpoint file path"""
        return self.checkpoint_dir / f"{project_id}.checkpoint.json"

    def _get_backoff_delay(self) -> float:
        """Calculate exponential backoff delay"""
        delay = self.base_delay * (2 ** self.retry_count)
        return min(delay, self.max_delay)

    async def check_connection(self) -> bool:
        """Check if server is reachable"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.config.api_base_url}/health")
                return response.status_code == 200
        except Exception:
            return False

    async def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        """Save checkpoint to local file"""
        self._current_checkpoint = checkpoint
        checkpoint_path = self._get_checkpoint_path(checkpoint.project_id)

        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

        self.console.print(f"[dim]💾 Checkpoint saved[/dim]", style="dim")

    async def load_checkpoint(self, project_id: str) -> Optional[WorkflowCheckpoint]:
        """Load checkpoint from local file"""
        checkpoint_path = self._get_checkpoint_path(project_id)

        if not checkpoint_path.exists():
            return None

        try:
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
            return WorkflowCheckpoint.from_dict(data)
        except Exception as e:
            self.console.print(f"[red]Failed to load checkpoint: {e}[/red]")
            return None

    async def delete_checkpoint(self, project_id: str) -> None:
        """Delete checkpoint after successful completion"""
        checkpoint_path = self._get_checkpoint_path(project_id)
        if checkpoint_path.exists():
            checkpoint_path.unlink()
        self._current_checkpoint = None

    async def list_checkpoints(self) -> list:
        """List all available checkpoints"""
        checkpoints = []

        for path in self.checkpoint_dir.glob("*.checkpoint.json"):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                checkpoints.append({
                    "project_id": data.get("project_id"),
                    "workflow_type": data.get("workflow_type"),
                    "current_step": data.get("current_step"),
                    "timestamp": data.get("timestamp"),
                    "can_resume": data.get("retry_count", 0) < data.get("max_retries", 3)
                })
            except Exception:
                continue

        return sorted(checkpoints, key=lambda x: x.get("timestamp", 0), reverse=True)

    async def start_heartbeat(self, project_id: str) -> None:
        """Start heartbeat to keep connection alive"""
        async def heartbeat_loop():
            while True:
                try:
                    await asyncio.sleep(self.heartbeat_interval)
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        await client.post(
                            f"{self.config.api_base_url}/resume/heartbeat/{project_id}",
                            headers={"Authorization": f"Bearer {self.config.auth_token}"}
                        )
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass  # Heartbeat failure is not critical

        self._heartbeat_task = asyncio.create_task(heartbeat_loop())

    async def stop_heartbeat(self) -> None:
        """Stop heartbeat task"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

    async def stream_with_retry(
        self,
        url: str,
        data: dict,
        on_event: Optional[Callable[[dict], None]] = None,
        on_checkpoint: Optional[Callable[[WorkflowCheckpoint], None]] = None
    ) -> AsyncGenerator[dict, None]:
        """
        Stream SSE events with automatic retry on disconnection.

        Args:
            url: API endpoint URL
            data: Request data
            on_event: Callback for each event
            on_checkpoint: Callback when checkpoint is saved

        Yields:
            Parsed SSE events
        """
        project_id = data.get("project_id", f"project-{int(time.time())}")
        self.retry_count = 0

        while self.retry_count < self.max_retries:
            try:
                self.status = ConnectionStatus.CONNECTED

                # Start heartbeat
                await self.start_heartbeat(project_id)

                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream(
                        "POST",
                        url,
                        json=data,
                        headers={
                            "Authorization": f"Bearer {self.config.auth_token}",
                            "Content-Type": "application/json",
                            "Accept": "text/event-stream"
                        }
                    ) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            raise Exception(f"Server error: {response.status_code} - {error_text}")

                        # Process SSE stream
                        async for line in response.aiter_lines():
                            if not line or not line.startswith("data:"):
                                continue

                            try:
                                event_data = json.loads(line[5:].strip())

                                # Save checkpoint on progress events
                                if event_data.get("type") in ["step_complete", "file_created", "progress"]:
                                    checkpoint = WorkflowCheckpoint(
                                        project_id=project_id,
                                        workflow_type=data.get("workflow_type", "generation"),
                                        current_step=event_data.get("step", "unknown"),
                                        completed_steps=event_data.get("completed_steps", []),
                                        generated_files=event_data.get("generated_files", []),
                                        pending_files=event_data.get("pending_files", []),
                                        context=event_data.get("context", {}),
                                        timestamp=time.time(),
                                        retry_count=self.retry_count
                                    )
                                    await self.save_checkpoint(checkpoint)
                                    if on_checkpoint:
                                        on_checkpoint(checkpoint)

                                # Callback
                                if on_event:
                                    on_event(event_data)

                                yield event_data

                                # Check for completion
                                if event_data.get("type") == "complete":
                                    await self.delete_checkpoint(project_id)
                                    await self.stop_heartbeat()
                                    return

                            except json.JSONDecodeError:
                                continue

                # Stream completed successfully
                await self.delete_checkpoint(project_id)
                await self.stop_heartbeat()
                return

            except (httpx.ConnectError, httpx.ReadError, httpx.WriteError, ConnectionError) as e:
                # Network error - attempt reconnection
                self.status = ConnectionStatus.DISCONNECTED
                await self.stop_heartbeat()

                self.retry_count += 1
                delay = self._get_backoff_delay()

                if self.retry_count < self.max_retries:
                    # Save checkpoint with error
                    if self._current_checkpoint:
                        self._current_checkpoint.error_message = str(e)
                        self._current_checkpoint.retry_count = self.retry_count
                        await self.save_checkpoint(self._current_checkpoint)

                    self.console.print(
                        f"\n[yellow]⚠️  Connection lost. Retrying in {delay:.1f}s... "
                        f"(attempt {self.retry_count}/{self.max_retries})[/yellow]"
                    )

                    self.status = ConnectionStatus.RECONNECTING

                    # Wait with progress indicator
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=self.console,
                        transient=True
                    ) as progress:
                        task = progress.add_task("Reconnecting...", total=None)
                        await asyncio.sleep(delay)

                    # Check if server is back
                    if await self.check_connection():
                        self.console.print("[green]✓ Reconnected! Resuming...[/green]")
                        # Continue the loop to retry
                        continue
                    else:
                        self.console.print("[yellow]Server still unavailable, retrying...[/yellow]")
                        continue

            except asyncio.CancelledError:
                # User cancelled
                self.status = ConnectionStatus.DISCONNECTED
                await self.stop_heartbeat()

                if self._current_checkpoint:
                    self._current_checkpoint.error_message = "Cancelled by user"
                    await self.save_checkpoint(self._current_checkpoint)

                self.console.print("\n[yellow]Operation cancelled. Progress saved.[/yellow]")
                raise

            except Exception as e:
                # Other error
                self.status = ConnectionStatus.FAILED
                await self.stop_heartbeat()

                if self._current_checkpoint:
                    self._current_checkpoint.error_message = str(e)
                    await self.save_checkpoint(self._current_checkpoint)

                self.console.print(f"\n[red]Error: {e}[/red]")
                raise

        # Max retries exceeded
        self.status = ConnectionStatus.FAILED
        self.console.print(
            f"\n[red]❌ Failed after {self.max_retries} attempts. "
            f"Your progress has been saved.[/red]"
        )
        self.console.print(
            f"[yellow]Run 'bharatbuild resume {project_id}' to continue later.[/yellow]"
        )

    async def resume_workflow(self, project_id: str) -> AsyncGenerator[dict, None]:
        """
        Resume an interrupted workflow from checkpoint.

        Args:
            project_id: Project ID to resume

        Yields:
            SSE events from resumed workflow
        """
        checkpoint = await self.load_checkpoint(project_id)

        if not checkpoint:
            self.console.print(f"[red]No checkpoint found for project {project_id}[/red]")
            return

        if checkpoint.retry_count >= checkpoint.max_retries:
            self.console.print(
                f"[red]Maximum retries ({checkpoint.max_retries}) exceeded for this project.[/red]"
            )
            self.console.print("[yellow]Use '/resume --force' to try again anyway.[/yellow]")
            return

        # Show resume info
        self.console.print(Panel(
            f"[bold]Resuming Project: {project_id}[/bold]\n\n"
            f"Last step: [cyan]{checkpoint.current_step}[/cyan]\n"
            f"Files generated: [green]{len(checkpoint.generated_files)}[/green]\n"
            f"Files remaining: [yellow]{len(checkpoint.pending_files)}[/yellow]\n"
            f"Retry attempt: {checkpoint.retry_count + 1}/{checkpoint.max_retries}",
            title="🔄 Resume",
            border_style="cyan"
        ))

        # Update retry count
        checkpoint.retry_count += 1
        await self.save_checkpoint(checkpoint)

        # Call resume API
        url = f"{self.config.api_base_url}/resume/{project_id}"

        try:
            async for event in self.stream_with_retry(
                url,
                {"project_id": project_id},
            ):
                yield event

        except Exception as e:
            self.console.print(f"[red]Resume failed: {e}[/red]")

    async def check_resumable(self) -> list:
        """
        Check for any resumable projects.

        Returns list of projects that can be resumed.
        """
        checkpoints = await self.list_checkpoints()
        resumable = [cp for cp in checkpoints if cp.get("can_resume")]

        if resumable:
            self.console.print(
                f"\n[yellow]📋 Found {len(resumable)} interrupted project(s):[/yellow]"
            )
            for cp in resumable:
                self.console.print(
                    f"  • {cp['project_id']} - Step: {cp['current_step']}"
                )
            self.console.print(
                "[dim]Use '/resume <project_id>' to continue[/dim]\n"
            )

        return resumable


# Convenience function for CLI
async def create_reconnection_handler(config: CLIConfig, console: Console) -> ReconnectionHandler:
    """Create and initialize reconnection handler"""
    handler = ReconnectionHandler(config, console)

    # Check for resumable projects on startup
    await handler.check_resumable()

    return handler
