from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


def send_xdot(commands: List[str]) -> subprocess.CompletedProcess[str]:
    """Send raw xdotool commands to the X server.

    Example::
        send_xdot(["mousemove 400 300", "click 1"])
    """
    joined = " && ".join(f"xdotool {c}" for c in commands)
    return subprocess.run(
        ["bash", "-c", joined], capture_output=True, text=True, env={"DISPLAY": ":1"}
    ) 