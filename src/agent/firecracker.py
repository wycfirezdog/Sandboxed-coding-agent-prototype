from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


@dataclass
class VMHandle:
    id: str
    socket_path: Path
    workdir: Path


class MicroVMManager:
    """Very lightweight Firecracker wrapper (prototype).

    For the purpose of this reference implementation, the methods are
    stubs that *pretend* to create micro-VMs.  Integrating the actual
    Firecracker control socket & jailer is left as an exercise.
    """

    def __init__(self, base_image: str = "ubuntu-22.04.ext4"):
        self.base_image = base_image
        self.vm_root = Path(tempfile.gettempdir()) / "agent_microvms"
        self.vm_root.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def spawn(self) -> VMHandle:
        vm_id = str(uuid.uuid4())
        vm_dir = self.vm_root / vm_id
        vm_dir.mkdir()

        # (Prototype) copy base image to vm_dir
        rootfs = vm_dir / "rootfs.ext4"
        try:
            shutil.copy(self.base_image, rootfs)
        except FileNotFoundError:
            # base image not shipped; create empty placeholder
            rootfs.touch()

        socket_path = vm_dir / "firecracker.socket"

        # Instead of actually invoking firecracker, just create socket file stub
        socket_path.touch()

        return VMHandle(id=vm_id, socket_path=socket_path, workdir=vm_dir)

    def terminate(self, vm: VMHandle) -> None:
        shutil.rmtree(vm.workdir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Context manager helper
    # ------------------------------------------------------------------
    @contextmanager
    def microvm(self) -> Iterator[VMHandle]:
        vm = self.spawn()
        try:
            yield vm
        finally:
            self.terminate(vm) 