#!/usr/bin/env python3
"""Verify immutable public release tags, assets, and checksums."""

from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


RELEASE_TAG = "v1.0.1"
RELEASE_COMMIT = "d7cba1419145e6c75fe69ad63172af5f5abe5028"
SUBMITTED_TAG = "v1.0.0"
SUBMITTED_COMMIT = "1d2ab45e516ef4167c6c4c4265da5b533b2eab78"
ARCHIVE_NAME = "SHM-EM-v1.0.1.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remote_commit(repo: Path, tag: str) -> str:
    output = subprocess.run(
        ["git", "ls-remote", "origin", f"refs/tags/{tag}^{{}}"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    ).stdout.strip()
    return output.split()[0] if output else ""


def request_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "SHM-EM-release-verifier"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    output = repo / "artifacts/revision/final-manuscript-review/release-publication-verification.json"
    archive = repo / "artifacts/releases" / ARCHIVE_NAME
    local_hash = sha256(archive)
    api = json.loads(request_bytes(f"https://api.github.com/repos/lja666/SHM-EM/releases/tags/{RELEASE_TAG}"))
    assets = {asset["name"]: asset["browser_download_url"] for asset in api.get("assets", [])}
    published_checksum = request_bytes(assets[f"{ARCHIVE_NAME}.sha256"]).decode("utf-8").strip()
    checks = {
        "releaseTagCommit": remote_commit(repo, RELEASE_TAG) == RELEASE_COMMIT,
        "submittedTagUnchanged": remote_commit(repo, SUBMITTED_TAG) == SUBMITTED_COMMIT,
        "releasePublished": api.get("tag_name") == RELEASE_TAG and not api.get("draft"),
        "archivePublished": ARCHIVE_NAME in assets,
        "checksumPublished": f"{ARCHIVE_NAME}.sha256" in assets,
        "publishedChecksumMatchesLocal": published_checksum == f"{local_hash}  {ARCHIVE_NAME}",
    }
    value = {
        "schemaVersion": "shm-em-public-release-verification-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "release": {
            "tag": RELEASE_TAG,
            "fixedCommit": RELEASE_COMMIT,
            "url": api.get("html_url"),
            "archive": ARCHIVE_NAME,
            "sha256": local_hash,
            "assets": assets,
        },
        "submittedRelease": {"tag": SUBMITTED_TAG, "fixedCommit": SUBMITTED_COMMIT},
        "checks": checks,
        "pass": all(checks.values()),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"pass": value["pass"], "checks": checks}, indent=2))
    return 0 if value["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
