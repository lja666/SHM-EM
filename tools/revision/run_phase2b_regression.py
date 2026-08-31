#!/usr/bin/env python3
"""Run the final Phase 2B regression set and record reproducible command evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used for PIT_PRE tests.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/revision/manuscript/phase2b-final-regression.json"),
    )
    return parser.parse_args()


def run_check(
    identifier: str,
    command: list[str],
    workdir: Path,
    repository: Path,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=workdir,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = (completed.stdout + "\n" + completed.stderr).strip()
    return {
        "id": identifier,
        "command": [Path(command[0]).name, *command[1:]],
        "workingDirectory": workdir.relative_to(repository).as_posix(),
        "startedAtUtc": started_at.isoformat(),
        "durationSeconds": round(time.perf_counter() - started, 3),
        "exitCode": completed.returncode,
        "pass": completed.returncode == 0,
        "outputTail": output[-12000:],
    }


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment.setdefault("MAVEN_OPTS", "-Dfile.encoding=UTF-8")
    checks = [
        run_check(
            "BACKEND_MAVEN_TEST_PACKAGE",
            ["mvn.cmd", "-q", "test", "package"],
            repo / "src/backend",
            repo,
            environment,
        ),
        run_check(
            "PIT_PRE_UNITTEST",
            [args.python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
            repo / "src/pit_pre",
            repo,
            environment,
        ),
        run_check(
            "FRONTEND_PRODUCTION_BUILD",
            ["npm.cmd", "run", "build"],
            repo / "src/frontend",
            repo,
            environment,
        ),
    ]
    result = {
        "schemaVersion": "shm-em-phase2b-final-regression-v1",
        "finalCoreFreezeV3": "eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "pass": all(item["pass"] for item in checks),
    }
    output = repo / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "pass": result["pass"],
                "checks": [
                    {key: item[key] for key in ("id", "exitCode", "durationSeconds")}
                    for item in checks
                ],
                "output": output.relative_to(repo).as_posix(),
            },
            indent=2,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
