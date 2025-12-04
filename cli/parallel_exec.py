"""
BharatBuild CLI Parallel Tool Execution

Execute multiple tools in parallel for better performance.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from typing import Optional, List, Dict, Any, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.live import Live
from rich.table import Table


T = TypeVar('T')


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ParallelTask(Generic[T]):
    """A task to execute in parallel"""
    id: str
    name: str
    func: Callable[..., T]
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[T] = None
    error: Optional[Exception] = None
    start_time: float = 0
    end_time: float = 0
    priority: int = 0  # Higher = more priority


@dataclass
class ExecutionResult:
    """Result of parallel execution"""
    total_tasks: int
    completed: int
    failed: int
    cancelled: int
    total_time: float
    results: Dict[str, Any]
    errors: Dict[str, Exception]


class ParallelExecutor:
    """
    Execute multiple tasks in parallel.

    Usage:
        executor = ParallelExecutor(console, max_workers=4)

        # Add tasks
        executor.add_task("read_file", read_file, args=("path/to/file",))
        executor.add_task("fetch_url", fetch_url, args=("http://example.com",))

        # Execute all
        results = executor.execute_all()

        # Or execute with progress
        results = executor.execute_with_progress()
    """

    def __init__(
        self,
        console: Console,
        max_workers: int = 4,
        timeout: float = 60.0
    ):
        self.console = console
        self.max_workers = max_workers
        self.timeout = timeout
        self._tasks: List[ParallelTask] = []
        self._lock = Lock()

    def add_task(
        self,
        task_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: Dict[str, Any] = None,
        name: str = "",
        priority: int = 0
    ) -> ParallelTask:
        """Add a task to execute"""
        task = ParallelTask(
            id=task_id,
            name=name or task_id,
            func=func,
            args=args,
            kwargs=kwargs or {},
            priority=priority
        )
        self._tasks.append(task)
        return task

    def clear_tasks(self):
        """Clear all tasks"""
        self._tasks.clear()

    def execute_all(self, show_progress: bool = False) -> ExecutionResult:
        """Execute all tasks in parallel"""
        if not self._tasks:
            return ExecutionResult(0, 0, 0, 0, 0.0, {}, {})

        start_time = time.time()

        # Sort by priority
        sorted_tasks = sorted(self._tasks, key=lambda t: -t.priority)

        results = {}
        errors = {}
        completed = 0
        failed = 0
        cancelled = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task: Dict[Future, ParallelTask] = {}

            for task in sorted_tasks:
                task.status = TaskStatus.RUNNING
                task.start_time = time.time()

                future = executor.submit(task.func, *task.args, **task.kwargs)
                future_to_task[future] = task

            # Collect results
            for future in as_completed(future_to_task, timeout=self.timeout):
                task = future_to_task[future]

                try:
                    result = future.result()
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.end_time = time.time()
                    results[task.id] = result
                    completed += 1

                except Exception as e:
                    task.error = e
                    task.status = TaskStatus.FAILED
                    task.end_time = time.time()
                    errors[task.id] = e
                    failed += 1

        total_time = time.time() - start_time

        return ExecutionResult(
            total_tasks=len(self._tasks),
            completed=completed,
            failed=failed,
            cancelled=cancelled,
            total_time=total_time,
            results=results,
            errors=errors
        )

    def execute_with_progress(self) -> ExecutionResult:
        """Execute tasks with Rich progress display"""
        if not self._tasks:
            return ExecutionResult(0, 0, 0, 0, 0.0, {}, {})

        start_time = time.time()
        sorted_tasks = sorted(self._tasks, key=lambda t: -t.priority)

        results = {}
        errors = {}
        completed = 0
        failed = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        ) as progress:

            # Main progress bar
            main_task = progress.add_task(
                "Executing tasks...",
                total=len(sorted_tasks)
            )

            # Individual task progress
            task_progress: Dict[str, TaskID] = {}
            for task in sorted_tasks:
                task_progress[task.id] = progress.add_task(
                    f"  {task.name}",
                    total=1,
                    visible=True
                )

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_task: Dict[Future, ParallelTask] = {}

                for task in sorted_tasks:
                    task.status = TaskStatus.RUNNING
                    task.start_time = time.time()

                    future = executor.submit(task.func, *task.args, **task.kwargs)
                    future_to_task[future] = task

                for future in as_completed(future_to_task, timeout=self.timeout):
                    task = future_to_task[future]

                    try:
                        result = future.result()
                        task.result = result
                        task.status = TaskStatus.COMPLETED
                        task.end_time = time.time()
                        results[task.id] = result
                        completed += 1

                        # Update progress
                        progress.update(task_progress[task.id], completed=1)
                        progress.update(
                            task_progress[task.id],
                            description=f"  [green]✓[/green] {task.name}"
                        )

                    except Exception as e:
                        task.error = e
                        task.status = TaskStatus.FAILED
                        task.end_time = time.time()
                        errors[task.id] = e
                        failed += 1

                        # Update progress
                        progress.update(task_progress[task.id], completed=1)
                        progress.update(
                            task_progress[task.id],
                            description=f"  [red]✗[/red] {task.name}"
                        )

                    progress.update(main_task, advance=1)

        total_time = time.time() - start_time

        return ExecutionResult(
            total_tasks=len(self._tasks),
            completed=completed,
            failed=failed,
            cancelled=0,
            total_time=total_time,
            results=results,
            errors=errors
        )

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get status of a specific task"""
        for task in self._tasks:
            if task.id == task_id:
                return task.status
        return None


class AsyncParallelExecutor:
    """
    Async version of parallel executor for IO-bound tasks.

    Usage:
        executor = AsyncParallelExecutor(console)

        async def main():
            executor.add_task("fetch1", fetch_data, args=("url1",))
            executor.add_task("fetch2", fetch_data, args=("url2",))
            results = await executor.execute_all()
    """

    def __init__(
        self,
        console: Console,
        max_concurrent: int = 10,
        timeout: float = 60.0
    ):
        self.console = console
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self._tasks: List[ParallelTask] = []
        self._semaphore: Optional[asyncio.Semaphore] = None

    def add_task(
        self,
        task_id: str,
        coro_func: Callable,
        args: tuple = (),
        kwargs: Dict[str, Any] = None,
        name: str = "",
        priority: int = 0
    ) -> ParallelTask:
        """Add an async task"""
        task = ParallelTask(
            id=task_id,
            name=name or task_id,
            func=coro_func,
            args=args,
            kwargs=kwargs or {},
            priority=priority
        )
        self._tasks.append(task)
        return task

    def clear_tasks(self):
        """Clear all tasks"""
        self._tasks.clear()

    async def execute_all(self) -> ExecutionResult:
        """Execute all async tasks"""
        if not self._tasks:
            return ExecutionResult(0, 0, 0, 0, 0.0, {}, {})

        start_time = time.time()
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        sorted_tasks = sorted(self._tasks, key=lambda t: -t.priority)

        results = {}
        errors = {}
        completed = 0
        failed = 0

        async def run_task(task: ParallelTask):
            nonlocal completed, failed

            async with self._semaphore:
                task.status = TaskStatus.RUNNING
                task.start_time = time.time()

                try:
                    result = await asyncio.wait_for(
                        task.func(*task.args, **task.kwargs),
                        timeout=self.timeout
                    )
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.end_time = time.time()
                    results[task.id] = result
                    completed += 1

                except asyncio.TimeoutError:
                    task.error = TimeoutError(f"Task {task.id} timed out")
                    task.status = TaskStatus.FAILED
                    task.end_time = time.time()
                    errors[task.id] = task.error
                    failed += 1

                except Exception as e:
                    task.error = e
                    task.status = TaskStatus.FAILED
                    task.end_time = time.time()
                    errors[task.id] = e
                    failed += 1

        # Run all tasks
        await asyncio.gather(*[run_task(t) for t in sorted_tasks])

        total_time = time.time() - start_time

        return ExecutionResult(
            total_tasks=len(self._tasks),
            completed=completed,
            failed=failed,
            cancelled=0,
            total_time=total_time,
            results=results,
            errors=errors
        )


class ToolParallelizer:
    """
    Parallelize AI tool calls.

    Usage:
        parallelizer = ToolParallelizer(console)

        # Queue multiple tool calls
        parallelizer.queue_tool("read", {"path": "file1.py"})
        parallelizer.queue_tool("read", {"path": "file2.py"})
        parallelizer.queue_tool("bash", {"command": "ls -la"})

        # Execute all
        results = parallelizer.execute_tools(tool_handler)
    """

    def __init__(self, console: Console, max_parallel: int = 4):
        self.console = console
        self.max_parallel = max_parallel
        self._queue: List[Dict[str, Any]] = []

    def queue_tool(self, tool_name: str, params: Dict[str, Any], priority: int = 0):
        """Queue a tool call"""
        self._queue.append({
            "tool": tool_name,
            "params": params,
            "priority": priority
        })

    def clear_queue(self):
        """Clear the queue"""
        self._queue.clear()

    def can_parallelize(self, tools: List[Dict]) -> List[List[Dict]]:
        """
        Group tools into parallelizable batches.

        Rules:
        - Read operations can always be parallelized
        - Write operations to different files can be parallelized
        - Bash commands are sequential by default (unless independent)
        """
        read_tools = []
        write_tools = []
        bash_tools = []
        other_tools = []

        for tool in tools:
            name = tool.get("tool", "")

            if name in ("read", "glob", "grep", "search"):
                read_tools.append(tool)
            elif name in ("write", "edit"):
                write_tools.append(tool)
            elif name == "bash":
                bash_tools.append(tool)
            else:
                other_tools.append(tool)

        batches = []

        # All reads can be parallel
        if read_tools:
            batches.append(read_tools)

        # Group writes by file (same file = sequential)
        if write_tools:
            file_groups: Dict[str, List[Dict]] = {}
            for tool in write_tools:
                path = tool.get("params", {}).get("path", "unknown")
                if path not in file_groups:
                    file_groups[path] = []
                file_groups[path].append(tool)

            # Different files can be parallel
            parallel_writes = [tools[0] for tools in file_groups.values()]
            batches.append(parallel_writes)

            # Sequential writes to same file
            for tools in file_groups.values():
                if len(tools) > 1:
                    for tool in tools[1:]:
                        batches.append([tool])

        # Bash is sequential
        for tool in bash_tools:
            batches.append([tool])

        # Other tools are sequential
        for tool in other_tools:
            batches.append([tool])

        return batches

    def execute_tools(
        self,
        tool_handler: Callable[[str, Dict], Any],
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """Execute queued tools with parallelization"""
        if not self._queue:
            return {}

        # Group into batches
        batches = self.can_parallelize(self._queue)

        all_results = {}

        executor = ParallelExecutor(
            self.console,
            max_workers=self.max_parallel
        )

        for batch in batches:
            executor.clear_tasks()

            for i, tool_call in enumerate(batch):
                tool_name = tool_call["tool"]
                params = tool_call["params"]

                executor.add_task(
                    task_id=f"{tool_name}_{i}",
                    func=tool_handler,
                    args=(tool_name, params),
                    name=f"{tool_name}: {list(params.values())[0] if params else ''}"[:40]
                )

            if show_progress and len(batch) > 1:
                result = executor.execute_with_progress()
            else:
                result = executor.execute_all()

            all_results.update(result.results)

        # Clear queue after execution
        self._queue.clear()

        return all_results


def show_parallel_results(console: Console, result: ExecutionResult):
    """Display parallel execution results"""
    table = Table(title="Parallel Execution Results", show_header=True, header_style="bold cyan")
    table.add_column("Metric")
    table.add_column("Value", justify="right")

    table.add_row("Total Tasks", str(result.total_tasks))
    table.add_row("Completed", f"[green]{result.completed}[/green]")
    table.add_row("Failed", f"[red]{result.failed}[/red]" if result.failed else "0")
    table.add_row("Total Time", f"{result.total_time:.2f}s")

    if result.total_tasks > 0:
        avg_time = result.total_time / result.total_tasks
        table.add_row("Avg Time/Task", f"{avg_time:.2f}s")

    console.print(table)

    # Show errors if any
    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for task_id, error in result.errors.items():
            console.print(f"  [red]✗[/red] {task_id}: {error}")
