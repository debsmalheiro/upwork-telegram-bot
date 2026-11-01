from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

MAX_IDS = 5000


class SeenState:
    def __init__(self, path: Path):
        self.path = Path(path)
        data = {}
        if self.path.exists():
            text = self.path.read_text().strip()
            data = json.loads(text) if text else {}
        self.initialized: bool = bool(data.get("initialized", False))
        self._ids = list(data.get("ids", []))
        self._set = set(self._ids)

    def __contains__(self, job_id: str) -> bool:
        return job_id in self._set

    def add_many(self, ids: Iterable[str]) -> None:
        for i in ids:
            if i not in self._set:
                self._ids.append(i)
                self._set.add(i)
        if len(self._ids) > MAX_IDS:
            self._ids = self._ids[-MAX_IDS:]
            self._set = set(self._ids)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"initialized": self.initialized, "ids": self._ids}, indent=0) + "\n")
