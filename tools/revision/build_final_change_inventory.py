#!/usr/bin/env python3
"""Build the Phase 1A.1 final inventory from the staged Git index."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import subprocess


REQUIRED_NEW_FILES = {
    "sql/shm_em_database/04_SHM_EM_persisted_prediction_integrity.sql",
    "src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/PersistedPredictionIntegrityHashService.java",
    "src/backend/src/test/java/mybatis/iem/em/modules/engineering/application/service/impl/PersistedPredictionIntegrityHashServiceTest.java",
    "src/pit_pre/tests/fixtures/persisted-integrity-fixture.json",
    "src/pit_pre/tests/test_persisted_integrity.py",
}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True,
    ).stdout.rstrip()


def category(path: str) -> str:
    if path.startswith("src/backend/src/main/") or path.startswith("src/pit_pre/pit_pre/"):
        return "production core"
    if path.startswith("sql/"):
        return "database/schema"
    if "/src/test/" in path or path.startswith("src/pit_pre/tests/"):
        return "tests"
    if path.startswith("tools/revision/"):
        return "revision tools"
    if path.startswith("artifacts/revision/"):
        return "evidence"
    return "documentation/other"


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    output_root = repo / "artifacts" / "revision" / "phase1a_1"
    status_lines = [line for line in git(repo, "diff", "--cached", "--name-status").splitlines() if line]
    numstat = {}
    for row in csv.reader(io.StringIO(git(repo, "diff", "--cached", "--numstat")), delimiter="\t"):
        if len(row) == 3:
            numstat[row[2]] = {"addedLines": row[0], "deletedLines": row[1]}
    entries = []
    for line in status_lines:
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        entries.append({
            "status": status,
            "path": path,
            "category": category(path),
            **numstat.get(path, {"addedLines": None, "deletedLines": None}),
        })
    paths = {entry["path"] for entry in entries}
    categories = {}
    for entry in entries:
        categories.setdefault(entry["category"], []).append(entry["path"])
    forbidden = sorted(path for path in paths if path.startswith("src/frontend/") or path.startswith("src/pit_pre/models/"))
    missing_required = sorted(REQUIRED_NEW_FILES - paths)
    inventory = {
        "schemaVersion": "shm-em-phase1a1-final-change-inventory-v1",
        "headBeforeCommitD": git(repo, "rev-parse", "HEAD"),
        "source": "git diff --cached",
        "stagedFileCount": len(entries),
        "stagedStat": git(repo, "diff", "--cached", "--stat"),
        "categories": categories,
        "entries": entries,
        "requiredNewFilesMissing": missing_required,
        "forbiddenFrozenFilesStaged": forbidden,
        "complete": bool(entries) and not missing_required and not forbidden,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "final-change-inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n",
    )
    lines = [
        "# Phase 1A.1 Final Staged Change Inventory", "",
        f"- HEAD before Commit D: `{inventory['headBeforeCommitD']}`",
        f"- Staged files: {len(entries)}",
        f"- Complete: `{str(inventory['complete']).lower()}`", "",
    ]
    for name in ("production core", "database/schema", "tests", "revision tools", "evidence", "documentation/other"):
        values = categories.get(name, [])
        lines.extend([f"## {name.title()}", ""])
        lines.extend(f"- `{value}`" for value in values)
        if not values:
            lines.append("- None")
        lines.append("")
    lines.extend(["## Staged Stat", "", "```text", inventory["stagedStat"], "```", ""])
    (output_root / "final-change-inventory.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"stagedFiles": len(entries), "complete": inventory["complete"]}, indent=2))
    return 0 if inventory["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
