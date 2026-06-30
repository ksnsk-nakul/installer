from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from installer.core.logger import console

STEPS = [
    (1, "OS / Environment Detection"),
    (2, "Environment Adapter Load"),
    (3, "API Verification & Stack Selection"),
    (4, "Stack Installation"),
    (5, "Post-Install Checks"),
]


class StepProgress:
    """Tracks the 5-step install flow with a Rich progress bar."""

    def __init__(self) -> None:
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[step]{task.description}[/step]"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        )
        self._task_id: TaskID | None = None

    def start(self) -> None:
        self._progress.start()
        self._task_id = self._progress.add_task(
            "Starting…", total=len(STEPS), completed=0
        )

    def advance(self, step: int) -> None:
        """Mark step N as complete and update description."""
        if self._task_id is None:
            return
        name = next((s[1] for s in STEPS if s[0] == step), f"Step {step}")
        self._progress.update(
            self._task_id,
            description=f"Step {step}: {name}",
            completed=step,
        )

    def finish(self, success: bool = True) -> None:
        if self._task_id is None:
            return
        label = "[success]✓ Complete[/success]" if success else "[error]✗ Failed[/error]"
        self._progress.update(self._task_id, description=label, completed=len(STEPS))
        self._progress.stop()

    @contextmanager
    def step(self, step_num: int) -> Generator[None, None, None]:
        """Context manager for a single step."""
        name = next((s[1] for s in STEPS if s[0] == step_num), f"Step {step_num}")
        if self._task_id is not None:
            self._progress.update(
                self._task_id,
                description=f"[dim]Step {step_num}: {name}…[/dim]",
            )
        try:
            yield
        finally:
            self.advance(step_num)
