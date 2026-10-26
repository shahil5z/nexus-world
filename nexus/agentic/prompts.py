"""Versioned prompt files, kept separate from code."""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

PROMPT_VERSION = "v1"
DIR = Path(__file__).parent / "prompts" / PROMPT_VERSION
SHARED = ("system", "safety", "domain_context")


@lru_cache(maxsize=None)
def load(name: str) -> str:
    return (DIR / f"{name}.md").read_text(encoding="utf-8").strip()


def instructions(role: str) -> str:
    return "\n\n".join([load(n) for n in SHARED] + [load(role)])


@lru_cache(maxsize=1)
def prompt_fingerprint() -> dict:
    h = hashlib.sha256()
    for p in sorted(DIR.glob("*.md")):
        h.update(p.name.encode()); h.update(p.read_bytes())
    return {"prompt_version": PROMPT_VERSION, "prompt_sha256": h.hexdigest()[:16]}
