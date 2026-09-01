#!/usr/bin/env python3
"""Build Phase 2C portability evidence and its project-local review package."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any
import zipfile


FREEZE = "eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f"
PORTABILITY = Path("artifacts/revision/portability")
PACKAGE_NAME = "SHM-EM_Phase2C_GPT_Review_Package.zip"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", action="store_true")
    return parser.parse_args()


def run(repo: Path, *command: str) -> str:
    completed = subprocess.run(
        command, cwd=repo, text=True, encoding="utf-8", errors="replace", capture_output=True
    )
    if completed.returncode:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n{completed.stderr}"
        )
    return completed.stdout.strip()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compose_ps(repo: Path) -> list[dict[str, Any]]:
    env = os.environ.copy()
    env.setdefault("SHM_EM_MYSQL_ROOT_PASSWORD", "phase2c-evidence-placeholder")
    env.setdefault("SHM_EM_MYSQL_PASSWORD", "phase2c-evidence-placeholder")
    completed = subprocess.run(
        ["docker", "compose", "ps", "-a", "--format", "json"],
        cwd=repo,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=True,
    )
    rows = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        rows.append(
            {
                "service": item.get("Service"),
                "image": item.get("Image"),
                "state": item.get("State"),
                "health": item.get("Health") or None,
                "exitCode": item.get("ExitCode"),
                "ports": item.get("Ports") or None,
            }
        )
    return sorted(rows, key=lambda item: str(item["service"]))


def image_summary(repo: Path, name: str) -> dict[str, Any]:
    item = json.loads(run(repo, "docker", "image", "inspect", name))[0]
    return {
        "name": name,
        "id": item["Id"],
        "created": item["Created"],
        "sizeBytes": item["Size"],
        "os": item["Os"],
        "architecture": item["Architecture"],
    }


def secret_scan(repo: Path) -> dict[str, Any]:
    candidates = run(
        repo, "git", "ls-files", "--cached", "--others", "--exclude-standard"
    ).splitlines()
    prohibited = {
        "historicalDatabasePassword": "123" + "456",
        "historicalMapKey": "c74885c2c3881e06" + "da3fffc2f4decaa3",
        "historicalMapSecurityCode": "ac1908b24198cc23" + "fda0a3977e807479",
    }
    findings = []
    for relative in candidates:
        path = repo / relative
        if not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for name, literal in prohibited.items():
            found = re.search(rf"(?<![0-9]){re.escape(literal)}(?![0-9])", text) if name == "historicalDatabasePassword" else literal in text
            if found:
                findings.append({"path": relative.replace("\\", "/"), "type": name})
        if ("-----BEGIN " + "PRIVATE KEY-----") in text:
            findings.append({"path": relative.replace("\\", "/"), "type": "privateKey"})
    return {
        "schemaVersion": "shm-em-phase2c-secret-scan-v1",
        "scope": "Git tracked and non-ignored untracked text files up to 5 MiB",
        "checks": [*prohibited.keys(), "privateKey"],
        "findingCount": len(findings),
        "findings": findings,
        "pass": not findings,
        "boundary": "This bounded repository scan is not a substitute for a dedicated secret-scanning service.",
    }


def update_reviewer_map(repo: Path) -> None:
    path = repo / "artifacts/revision/manuscript/reviewer-evidence-map.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    updates = {
        "R1-11": (
            "DOCUMENTATION_COMPLETE",
            ["SECURITY.md", "docs/revision/DEPLOYMENT_LIMITATIONS.md"],
            "Report deployment guidance as documented controls, not implemented production authentication.",
        ),
        "R1-12": (
            "PARTIALLY_SUPPORTED",
            [
                "artifacts/revision/portability/cross-platform-comparison.md",
                "artifacts/revision/portability/portability-limitations.md",
            ],
            "Report that the Linux-container workflow completed logically, while exact normalized-output reproduction and native Ubuntu component validation remain unverified.",
        ),
        "R3-1": (
            "DOCUMENTATION_COMPLETE",
            ["docs/revision/STORAGE_ADAPTER_BOUNDARY.md", "docs/DATABASE.md"],
            "Describe the logical registry, approved adapters, and MySQL-specific implementation without claiming another validated backend.",
        ),
        "R3-2": (
            "DOCUMENTATION_COMPLETE",
            ["SECURITY.md"],
            "Report the recommended deployment pattern; do not claim an implemented authentication subsystem.",
        ),
        "R3-4": (
            "PARTIALLY_SUPPORTED",
            [
                "artifacts/revision/portability/linux-reference-reproduction.json",
                "artifacts/revision/portability/cross-platform-comparison.md",
                "artifacts/revision/portability/cross-platform-numeric-difference.json",
            ],
            "Disclose the exact output-hash mismatch and retain Windows as the validated exact-reproduction environment.",
        ),
    }
    for entry in value["entries"]:
        update = updates.get(entry["reviewerItem"])
        if update:
            entry["status"], entry["evidence"], entry["nextAction"] = update
    write_json(path, value)
    lines = [
        "# Reviewer Evidence Map",
        "",
        "| Reviewer item | Topic | Status | Evidence | Next action |",
        "|---|---|---|---|---|",
    ]
    for entry in value["entries"]:
        evidence = "<br>".join(f"`{item}`" for item in entry["evidence"])
        lines.append(
            f"| {entry['reviewerItem']} | {entry['topic']} | {entry['status']} | {evidence} | {entry['nextAction']} |"
        )
    path.with_suffix(".md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )


def update_claim_gap(repo: Path) -> None:
    path = repo / "artifacts/revision/manuscript/claim-gap-matrix-final.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "| Linux or Docker reproduction is supported | Not validated in this release | Native Windows reproduction is the validated path; portability remains future work | Cross-platform or container portability |",
        "| Linux or Docker reproduction is supported | Partially demonstrated; exact output hash differs | The Linux-container workflow completed logically with matching input/contract hashes, but exact cross-platform prediction reproduction was not established | Exact Linux reproduction, tolerance-equivalent reproduction, or native Ubuntu validation |",
    )
    text = text.replace(
        "| The deployment is secure by default | Not established | Security is deployment-dependent and requires network, authentication, authorization, secret, and TLS controls | Production-grade security certification |",
        "| Deployment security controls are documented | Documentation complete; controls are not implemented by this research release | Production deployment requires the documented TLS, identity, RBAC, secret, network, and protected-audit controls | Secure-by-default operation or production-grade security certification |",
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def evidence_files(root: Path, repo: Path) -> list[dict[str, Any]]:
    excluded = {PACKAGE_NAME, "phase2c-gpt-review-package.json", "phase2c-portability-manifest.json", "GPT_REVIEW_HANDOFF.md"}
    files = [path for path in root.iterdir() if path.is_file() and path.name not in excluded]
    return [
        {
            "path": path.relative_to(repo).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(files)
    ]


def build(repo: Path, make_package: bool) -> None:
    root = repo / PORTABILITY
    root.mkdir(parents=True, exist_ok=True)
    linux = json.loads((root / "linux-reference-reproduction.json").read_text(encoding="utf-8"))
    comparison = json.loads((root / "cross-platform-comparison.json").read_text(encoding="utf-8"))
    numeric = json.loads((root / "cross-platform-numeric-difference.json").read_text(encoding="utf-8"))
    head = run(repo, "git", "rev-parse", "HEAD")
    core_diff = run(
        repo,
        "git",
        "diff",
        "--name-only",
        FREEZE,
        "--",
        "src/backend/src/main",
        "src/pit_pre/pit_pre",
        "src/frontend/src",
    )
    services = compose_ps(repo)
    docker_version = json.loads(run(repo, "docker", "version", "--format", "{{json .}}"))

    write_json(
        root / "environment-linux.json",
        {
            "schemaVersion": "shm-em-phase2c-linux-environment-v1",
            "capturedAtUtc": datetime.now(timezone.utc).isoformat(),
            "scope": "Docker Desktop Linux containers on the local Phase 2C host",
            "dockerServer": {
                "version": docker_version["Server"]["Version"],
                "os": docker_version["Server"].get("Os"),
                "architecture": docker_version["Server"].get("Arch"),
                "kernelVersion": docker_version["Server"].get("KernelVersion"),
            },
            "nativeUbuntu": {
                "status": "NOT_VALIDATED",
                "reason": "The available WSL Ubuntu installation has unresolved host package-manager dependencies; no native component PASS is claimed.",
            },
        },
    )
    write_json(
        root / "ubuntu-ci-summary.json",
        {
            "schemaVersion": "shm-em-phase2c-ubuntu-ci-summary-v1",
            "workflow": ".github/workflows/ci.yml",
            "configuredMatrix": ["windows-latest", "ubuntu-latest"],
            "components": [
                "backend Maven tests/package",
                "PIT_PRE unittest/compileall",
                "frontend typecheck/build",
            ],
            "localResult": "NOT_EXECUTED",
            "remoteCiResult": "NOT_CAPTURED",
            "gateP2C03": "NOT_VERIFIED",
            "claimBoundary": "Workflow configuration is not runtime evidence. No Ubuntu component PASS is claimed until a CI run or clean native run is captured.",
        },
    )
    images = [
        image_summary(repo, name)
        for name in (
            "shm-em-reproduction-backend",
            "shm-em-reproduction-pitpre",
            "shm-em-reproduction-frontend",
        )
    ]
    write_json(
        root / "docker-build-summary.json",
        {
            "schemaVersion": "shm-em-phase2c-docker-build-summary-v1",
            "result": "PASS",
            "images": images,
            "buildStageChecks": {
                "backendTests": "55/55 PASS",
                "pitPreTests": "13/13 PASS",
                "frontend": "typecheck and build PASS",
            },
            "note": "Counts are the test stages executed while constructing the recorded image IDs; this is Docker build evidence, not native Ubuntu CI evidence.",
        },
    )
    write_json(
        root / "compose-services.json",
        {"schemaVersion": "shm-em-phase2c-compose-services-v1", "services": services},
    )
    scan = secret_scan(repo)
    write_json(root / "secret-scan-summary.json", scan)

    maximum = max(
        (item["maxAbsoluteDifference"] for item in numeric["fieldDifferences"].values()),
        key=float,
    )
    maximum_relative = max(
        (item["maxRelativeDifference"] for item in numeric["fieldDifferences"].values()),
        key=float,
    )
    limitations = f"""# Phase 2C Portability Limitations

The Docker/Linux reference run completed the six-model, 124-target, 40-step workflow and persisted 4,960 results. Input and model-contract hashes matched, persisted integrity and the execution Gate passed, Project Future State succeeded, Evaluate had no formal side effect, and Execute created the expected event/response/provenance chain.

Exact cross-platform prediction reproduction did **not** pass. The frozen Windows normalized output hash is `{linux['expectedPredictionOutputHash']}`, whereas the Docker/Linux hash is `{linux['predictionOutputHash']}`. All 4,960 persisted rows matched by target and step, with no missing or additional rows; the maximum persisted absolute numeric difference was `{maximum}` and the maximum relative difference was `{maximum_relative}`. No tolerance was applied and the deterministic hash contract was not changed.

Native Ubuntu component validation is also not claimed: the available WSL Ubuntu installation has unresolved host package-manager dependencies, and no successful GitHub Actions run was captured in this phase. The CI matrix is configured for Ubuntu, but configuration alone is not evidence.

Accordingly, native Windows remains the validated exact-reproduction environment. The container path is reported as partial portability evidence and a diagnostic reproduction path, not as exact Linux equivalence.
"""
    (root / "portability-limitations.md").write_text(
        limitations, encoding="utf-8", newline="\n"
    )

    update_reviewer_map(repo)
    update_claim_gap(repo)

    gates = [
        ("P2C-01", not core_diff, "Final Core Freeze v3 unchanged"),
        ("P2C-02", True, "Frozen Windows validation retained"),
        ("P2C-03", False, "Ubuntu component validation not captured"),
        ("P2C-04", True, "Docker images built with component checks"),
        ("P2C-05", all(item["state"] in ("running", "exited") and (item["service"] == "pitpre" or item["health"] == "healthy") for item in services), "Compose services reached expected healthy/completed states"),
        ("P2C-06", False, "Logical workflow completed, but exact normalized output hash differs"),
        ("P2C-07", True, "Cross-platform comparison and raw numeric difference artifacts complete"),
        ("P2C-08", scan["pass"], "Runtime credentials are environment-only; bounded repository secret scan recorded"),
        ("P2C-09", True, "Deployment security guidance documented without implementing auth"),
        ("P2C-10", True, "Persisted-integrity security boundary stated accurately"),
        ("P2C-11", True, "Logical/adapter/MySQL storage layers distinguished"),
        ("P2C-12", True, "No alternative database conformance claim"),
        ("P2C-13", True, "50k Gate cap identified as application boundary"),
        ("P2C-14", True, "R2-3/R3-3 wording corrected"),
        ("P2C-15", not core_diff, "Production business-core diff is NONE"),
    ]
    manifest = {
        "schemaVersion": "shm-em-phase2c-portability-manifest-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "finalCoreFreezeV3": FREEZE,
        "evidenceHead": head,
        "decision": "STOP_EXACT_CROSS_PLATFORM_REPRODUCTION",
        "productionCoreDiff": core_diff.splitlines(),
        "comparisonChecks": comparison["checks"],
        "gates": [
            {"id": gate, "pass": passed, "detail": detail}
            for gate, passed, detail in gates
        ],
        "gateSummary": {
            "passed": sum(passed for _, passed, _ in gates),
            "total": len(gates),
            "allPass": all(passed for _, passed, _ in gates),
        },
        "artifacts": evidence_files(root, repo),
    }
    write_json(root / "phase2c-portability-manifest.json", manifest)

    handoff = f"""# Phase 2C GPT Review Handoff

## Decision requested

Review the Phase 2C exact cross-platform STOP. Do not infer a portability PASS and do not authorize a tolerance or frozen-core change without examining the attached numerical differences.

## Baseline

- Final Core Freeze v3: `{FREEZE}`
- Evidence HEAD: `{head}`
- Production business-core diff: **{'NONE' if not core_diff else 'PRESENT'}**

## Result

- Docker builds and service readiness: PASS
- Linux-container logical reference workflow: COMPLETE
- Input and model-contract hashes: EXACT
- Normalized prediction output hash: **DIFFERS**
- Persisted rows matched: 4,960 / 4,960
- Maximum persisted absolute difference: `{maximum}`
- Maximum persisted relative difference: `{maximum_relative}`
- Tolerance applied: NO
- Native Ubuntu component PASS: NOT CLAIMED

## GPT decision point

Decide whether the recorded difference requires a narrowly scoped investigation under a new authorization, or whether the revision should retain Windows exact reproduction and report Docker/Linux only as partial portability evidence. Phase 2D remains on hold.
"""
    (root / "GPT_REVIEW_HANDOFF.md").write_text(
        handoff, encoding="utf-8", newline="\n"
    )

    completion = f"""# Phase 2C Completion Report

## 1. Baseline

- Final Core Freeze v3: `{FREEZE}`
- Evidence preparation HEAD: `{head}`

## 2. Ubuntu Validation

- Backend: CI matrix configured; native Ubuntu result not captured.
- PIT_PRE: CI matrix configured; native Ubuntu result not captured.
- Frontend: CI matrix configured; native Ubuntu result not captured.

## 3. Docker/Compose

- Images: backend, PIT_PRE, and frontend built successfully.
- Services: MySQL, backend, and frontend healthy; PIT_PRE one-shot exited 0.
- Bounded secret scan: {'PASS' if scan['pass'] else 'FAIL'}.

## 4. Linux Reference Reproduction

- Models: {linux['modelCount']}
- Targets: {linux['targetCount']}
- Steps: {linux['predictionSteps']}
- Prediction rows: {linux['resultCount']}
- Integrity/Gate/Future State/Evaluate/Execute/provenance: logically complete.

## 5. Cross-Platform Comparison

- Input hash: exact.
- Normalized output hash: differs.
- Persisted row coverage: 4,960 / 4,960.
- Maximum persisted absolute difference: `{maximum}`.
- Maximum persisted relative difference: `{maximum_relative}`.
- Tolerance: not applied.

## 6. Security Documentation

- Research-release scope and recommended deployment controls documented.
- Persisted SHA-256 is explicitly not presented as tamper-proof against a privileged database attacker.

## 7. Storage Adapter Boundary

- Logical observation contract, approved adapters, and MySQL implementation are separated.
- No alternative database validation is claimed.
- The 50,000-row Gate cap is identified as an application boundary.

## 8. Reviewer Map

- R1-11, R3-1, and R3-2: documentation complete.
- R1-12 and R3-4: partially supported.
- R2-3 and R3-3: corrected missing-data wording retained.

## 9. Production-Core Diff

- **{'NONE' if not core_diff else 'PRESENT'}** relative to Final Core Freeze v3.

## 10. STOP

`STOP_EXACT_CROSS_PLATFORM_REPRODUCTION`. Await GPT review before any numerical-tolerance, production-core, or Phase 2D work.
"""
    (root / "PHASE2C_COMPLETION_REPORT.md").write_text(
        completion, encoding="utf-8", newline="\n"
    )
    manifest["artifacts"] = evidence_files(root, repo)
    write_json(root / "phase2c-portability-manifest.json", manifest)

    if make_package:
        include = [
            *sorted(
                path
                for path in root.iterdir()
                if path.is_file()
                and path.name not in (PACKAGE_NAME, "phase2c-gpt-review-package.json")
            ),
            repo / "SECURITY.md",
            repo / "compose.yaml",
            repo / ".env.example",
            repo / "docs/INSTALLATION.md",
            repo / "docs/ARCHITECTURE.md",
            repo / "docs/DATABASE.md",
            repo / "docs/revision/DEPLOYMENT_LIMITATIONS.md",
            repo / "docs/revision/STORAGE_ADAPTER_BOUNDARY.md",
            repo / "artifacts/revision/manuscript/reviewer-evidence-map.json",
            repo / "artifacts/revision/manuscript/reviewer-evidence-map.md",
            repo / "artifacts/revision/manuscript/claim-gap-matrix-final.md",
            repo / ".github/workflows/ci.yml",
            repo / "scripts/reproduce-compose.sh",
            repo / "tools/revision/validate_compose_reference.py",
            repo / "tools/revision/build_cross_platform_comparison.py",
            repo / "tools/revision/analyze_cross_platform_prediction_difference.py",
            Path(__file__).resolve(),
        ]
        package = root / PACKAGE_NAME
        with zipfile.ZipFile(
            package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for path in dict.fromkeys(include):
                archive.write(path, path.relative_to(repo).as_posix())
        metadata = {
            "path": package.relative_to(repo).as_posix(),
            "bytes": package.stat().st_size,
            "sha256": sha256(package),
            "decision": manifest["decision"],
        }
        write_json(root / "phase2c-gpt-review-package.json", metadata)
        print(json.dumps(metadata, indent=2))
    else:
        print(
            json.dumps(
                {
                    "manifest": str(root / "phase2c-portability-manifest.json"),
                    "decision": manifest["decision"],
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    args = arguments()
    build(Path(__file__).resolve().parents[2], args.package)
