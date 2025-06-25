from __future__ import annotations

import json
import os
import time
from collections import deque
from pathlib import Path
from typing import Deque, List

MAX_TOKENS_DEFAULT = 32_000  # naive budget; one token ≈ 4 chars for rough calc


class ContextStore:
    """File-backed storage for arbitrarily long conversational context.

    Each message is stored as a JSON line with shape:
    {"role": "user"|"assistant", "content": "...", "ts": unix_epoch}
    """

    def __init__(self, path: str | Path, max_tokens: int = MAX_TOKENS_DEFAULT):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_tokens = max_tokens

        # Bootstrap file
        self.path.touch(exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def append(self, role: str, content: str) -> None:
        """Append one record and prune if budget exceeded."""
        record = {
            "role": role,
            "content": content,
            "ts": int(time.time()),
        }
        with self.path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._prune()

    def dump(self) -> List[dict]:
        """Return all messages as a list of dicts (oldest first)."""
        with self.path.open("r", encoding="utf-8") as fp:
            return [json.loads(line) for line in fp if line.strip()]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _prune(self) -> None:
        """Naive byte-size based pruning to keep file roughly <= max_tokens."""
        # Convert token budget to rough char budget
        char_budget = self.max_tokens * 4
        if self.path.stat().st_size <= char_budget:
            return

        # Read all, drop oldest lines until under budget
        lines: Deque[str] = deque()
        total = 0
        for line in reversed(self.path.read_text(encoding="utf-8").splitlines(True)):
            lines.appendleft(line)
            total += len(line)
            if total > char_budget:
                lines.popleft()
                break

        with self.path.open("w", encoding="utf-8") as fp:
            fp.writelines(list(lines)) 