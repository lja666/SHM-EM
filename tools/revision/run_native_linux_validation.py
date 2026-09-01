#!/usr/bin/env python3
"""Run SHM-EM component validation in a native Linux environment."""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import time
import xml.etree.ElementTree as ET
from typing import Any


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", default="python3")
    parser.add_argument("--maven", default="mvn")
    parser.add_argument("--npm", default="npm")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/revision/portability"),
    )
    return parser.parse_args()


def command_version(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, errors="replace", check=False)
    return (result.stdout + "\n" + result.stderr).strip()


def execute(identifier: str, command: list[str], workdir: Path, repo: Path) -> dict[str, Any]:
    started = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=workdir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    return {
        "id": identifier,
        "command": [Path(command[0]).name, *command[1:]],
        "workingDirectory": workdir.relative_to(repo).as_posix(),
        "exitCode": result.returncode,
        "durationSeconds": round(time.perf_counter() - started, 3),
        "pass": result.returncode == 0,
        "outputTail": output[-8000:],
    }


def backend_count(repo: Path) -> dict[str, int]:
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for path in (repo / "src/backend/target/surefire-reports").glob("TEST-*.xml"):
        root = ET.parse(path).getroot()
        for key in totals:
            totals[key] += int(root.attrib.get(key, "0"))
    totals["passed"] = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    return totals


def pit_pre_count(repo: Path) -> int:
    count = 0
    for path in (repo / "src/pit_pre/tests").glob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        count += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
            for node in ast.walk(tree)
        )
    return count


def os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    path = Path("/etc/os-release")
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
    return values


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    args = arguments()
    if platform.system() != "Linux":
        raise SystemExit("Native Linux validation must run on Linux")
    repo = Path(__file__).resolve().parents[2]
    output = repo / args.output_root
    checks = [
        execute("BACKEND_TEST_PACKAGE", [args.maven, "-q", "test", "package"], repo / "src/backend", repo),
        execute("PIT_PRE_UNITTEST", [args.python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], repo / "src/pit_pre", repo),
        execute("FRONTEND_NPM_CI", [args.npm, "ci"], repo / "src/frontend", repo),
        execute("FRONTEND_TYPECHECK", [args.npm, "run", "typecheck"], repo / "src/frontend", repo),
        execute("FRONTEND_BUILD", [args.npm, "run", "build"], repo / "src/frontend", repo),
    ]
    environment = {
        "schemaVersion": "shm-em-phase2c-linux-environment-v1",
        "capturedAtUtc": datetime.now(timezone.utc).isoformat(),
        "kernel": platform.release(),
        "machine": platform.machine(),
        "osRelease": os_release(),
        "java": command_version(["java", "-version"]),
        "maven": command_version([args.maven, "--version"]),
        "python": command_version([args.python, "--version"]),
        "node": command_version(["node", "--version"]),
        "npm": command_version([args.npm, "--version"]),
    }
    summary = {
        "schemaVersion": "shm-em-phase2c-native-linux-validation-v1",
        "environment": {"distribution": environment["osRelease"].get("PRETTY_NAME"), "kernel": environment["kernel"]},
        "checks": checks,
        "backend": backend_count(repo),
        "pitPre": {"testMethods": pit_pre_count(repo), "pass": checks[1]["pass"]},
        "frontend": {"npmCi": checks[2]["pass"], "typecheck": checks[3]["pass"], "build": checks[4]["pass"]},
        "allPass": all(item["pass"] for item in checks),
    }
    write(output / "environment-linux.json", environment)
    write(output / "ubuntu-ci-summary.json", summary)
    print(json.dumps({"distribution": summary["environment"]["distribution"], "backend": summary["backend"], "pitPre": summary["pitPre"], "frontend": summary["frontend"], "allPass": summary["allPass"]}, indent=2))
    return 0 if summary["allPass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
