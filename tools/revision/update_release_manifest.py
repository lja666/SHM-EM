#!/usr/bin/env python3
"""Refresh the curated release-manifest hashes from the current worktree."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


HASH_LINE = re.compile(r"^(?P<hash>[0-9a-f]{64})  (?P<path>[^\r\n]+)$", re.MULTILINE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    manifest = repo / "docs/RELEASE_MANIFEST.md"
    text = manifest.read_text(encoding="utf-8")
    text = re.sub(
        r"Release: SHM-EM [^\.]+\. Hash algorithm:",
        "Release: SHM-EM 1.0.1. Hash algorithm:",
        text,
        count=1,
    )

    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        relative = match.group("path")
        source = repo / relative
        if not source.is_file():
            missing.append(relative)
            return match.group(0)
        return f"{sha256(source)}  {relative}"

    updated = HASH_LINE.sub(replace, text)
    if missing:
        raise FileNotFoundError(f"Release-manifest sources missing: {', '.join(missing)}")
    manifest.write_text(updated, encoding="utf-8", newline="\n")
    print(f"Updated {len(HASH_LINE.findall(text))} curated release hashes for SHM-EM 1.0.1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
