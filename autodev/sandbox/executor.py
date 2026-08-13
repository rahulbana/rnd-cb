"""Run shell commands inside a project's sandbox with timeouts + streaming.

This is deliberately a subprocess executor (not Docker) so it works on any
machine out of the box. Commands are always run with ``cwd`` pinned to the
project's workspace directory. A wall-clock timeout prevents runaway builds
or hanging test processes.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Optional

LineCallback = Optional[Callable[[str], Awaitable[None]]]


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    timed_out: bool = False
    duration: float = 0.0
    extra: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


async def run_command(
    command: str,
    cwd: Path,
    timeout: int = 300,
    env: Optional[dict] = None,
    on_line: LineCallback = None,
) -> CommandResult:
    """Run ``command`` (shell) in ``cwd``; merge stderr into stdout.

    Streams each output line through ``on_line`` as it arrives.
    """
    cwd = Path(cwd)
    cwd.mkdir(parents=True, exist_ok=True)

    full_env = os.environ.copy()
    # Keep child output unbuffered/line-oriented where possible.
    full_env["PYTHONUNBUFFERED"] = "1"
    if env:
        full_env.update(env)

    loop = asyncio.get_event_loop()
    start = loop.time()

    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=full_env,
    )

    collected: list[str] = []

    async def _pump() -> None:
        assert proc.stdout is not None
        while True:
            raw = await proc.stdout.readline()
            if not raw:
                break
            line = raw.decode("utf-8", "replace").rstrip("\n")
            collected.append(line)
            if on_line:
                await on_line(line)

    timed_out = False
    try:
        await asyncio.wait_for(_pump(), timeout=timeout)
        await asyncio.wait_for(proc.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        timed_out = True
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()

    duration = loop.time() - start
    returncode = proc.returncode if proc.returncode is not None else -1
    return CommandResult(
        command=command,
        returncode=returncode,
        stdout="\n".join(collected),
        timed_out=timed_out,
        duration=round(duration, 2),
    )
