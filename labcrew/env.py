from __future__ import annotations

import os
from pathlib import Path


def load_local_env(root: Path | None = None) -> None:
    """Load simple KEY=VALUE pairs from local env files without overriding env vars."""
    base = root or Path.cwd()
    for path in (base / ".env", base / ".env.local"):
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)
