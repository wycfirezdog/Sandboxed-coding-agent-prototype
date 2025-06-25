from __future__ import annotations

import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class JobKind(str, Enum):
    shell = "shell"
    python = "python"
    typescript = "typescript"
    gui = "gui"  # xdot commands (to be executed inside VM)


@dataclass
class JobResult:
    stdout: str
    stderr: str
    returncode: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class Runner:
    """Thin wrapper that dispatches code to appropriate interpreters.

    NOTE: For the prototype we simply exec locally. In production this
    should be executed inside a Firecracker micro-VM for strong isolation.
    """

    def __init__(self, workdir: Path | str | None = None) -> None:
        self.workdir = Path(workdir or Path.cwd())
        self.workdir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def run(self, kind: JobKind, code: str) -> JobResult:
        """Execute *code* of *kind* and capture its output."""

        if kind == JobKind.shell:
            return self._run_shell(code)
        elif kind == JobKind.python:
            return self._run_python(code)
        elif kind == JobKind.typescript:
            return self._run_typescript(code)
        elif kind == JobKind.gui:
            return self._run_gui(code)
        else:
            raise ValueError(f"Unsupported job kind: {kind}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _run_shell(self, snippet: str) -> JobResult:
        proc = subprocess.run(
            snippet,
            shell=True,
            cwd=self.workdir,
            capture_output=True,
            text=True,
        )
        return JobResult(proc.stdout, proc.stderr, proc.returncode)

    def _run_python(self, snippet: str) -> JobResult:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
            tmp.write(snippet)
            tmp_path = Path(tmp.name)
        proc = subprocess.run(
            ["python", str(tmp_path)],
            cwd=self.workdir,
            capture_output=True,
            text=True,
        )
        tmp_path.unlink(missing_ok=True)
        return JobResult(proc.stdout, proc.stderr, proc.returncode)

    def _run_typescript(self, snippet: str) -> JobResult:
        """Execute TS using `deno` if available, else `ts-node`.

        Falls back to error if neither interpreter is found.
        """
        # Write code to temp .ts file
        with tempfile.NamedTemporaryFile("w", suffix=".ts", delete=False) as tmp:
            tmp.write(snippet)
            tmp_path = Path(tmp.name)

        # Try Deno first
        for cmd in (["deno", "run", "--allow-all", str(tmp_path)],
                    ["ts-node", str(tmp_path)]):
            proc = subprocess.run(cmd, cwd=self.workdir, capture_output=True, text=True)
            if proc.returncode == 0 or "command not found" not in proc.stderr:
                tmp_path.unlink(missing_ok=True)
                return JobResult(proc.stdout, proc.stderr, proc.returncode)

        tmp_path.unlink(missing_ok=True)
        return JobResult("", "No TypeScript runtime (deno/ts-node) found", 1)

    def _run_gui(self, snippet: str) -> JobResult:
        """Forward GUI automation commands to xdotool inside the VM.

        For the prototype we simply invoke `xdotool` directly on the host.
        """
        proc = subprocess.run(
            ["bash", "-c", snippet],
            cwd=self.workdir,
            capture_output=True,
            text=True,
        )
        return JobResult(proc.stdout, proc.stderr, proc.returncode) 