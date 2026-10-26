"""Key loading. The key value is never logged, printed, returned or written anywhere."""
from __future__ import annotations

import os


def ensure_openai_key() -> bool:
    """Returns True if OPENAI_API_KEY is available. Optionally loads it from NEXUS_OPENAI_KEY_FILE."""
    if os.environ.get("OPENAI_API_KEY"):
        return True
    path = os.environ.get("NEXUS_OPENAI_KEY_FILE")
    if not path or not os.path.isfile(path):
        return False
    from dotenv import dotenv_values
    vals = dotenv_values(path)
    key = vals.get("OPENAI_API_KEY") or next((v for v in vals.values() if v), None)
    if not key:
        with open(path, encoding="utf-8") as f:
            raw = f.read().strip()
        key = raw if raw and "\n" not in raw and "=" not in raw else None
    if key:
        os.environ["OPENAI_API_KEY"] = key.strip().strip('"').strip("'")
        return True
    return False
