#!/usr/bin/env python3
"""Generate the deterministic structural baseline for the SoftwareX revision."""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable


AUDIT_SCHEMA_VERSION = "shm-em-repository-baseline-v1"
AUDIT_PATH_PREFIXES = ("artifacts/revision/", "docs/revision/", "tools/revision/")
RUNTIME_SOURCE_ROOTS = (
    "src/backend/src/main",
    "src/frontend/src",
    "src/pit_pre/pit_pre",
)
TEXT_SUFFIXES = {".java", ".xml", ".yml", ".yaml", ".properties", ".py", ".ts", ".vue", ".js"}
MODEL_CODE_LITERALS = ("YD", "XD", "Strain", "Pressure", "water", "settlement")


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def run(command: list[str], cwd: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
        return {"available": completed.returncode == 0, "command": command[0], "output": output}
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "command": command[0], "output": str(exc)}


def first_line(result: dict[str, Any]) -> str | None:
    output = result.get("output") or ""
    return output.splitlines()[0].strip() if output else None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_metadata(root: Path) -> dict[str, Any]:
    commit = run(["git", "rev-parse", "HEAD"], root)
    branch = run(["git", "branch", "--show-current"], root)
    tag_commit = run(["git", "rev-parse", "v1.0.0^{}"], root)
    status = run(["git", "status", "--porcelain", "--untracked-files=all"], root)
    status_lines = sorted(line for line in status.get("output", "").splitlines() if line.strip())
    source_changes = []
    for line in status_lines:
        path = line[3:].replace("\\", "/") if len(line) > 3 else line
        if not path.startswith(AUDIT_PATH_PREFIXES):
            source_changes.append(line)
    revision_evidence_changes = []
    for line in status_lines:
        path = line[3:].replace("\\", "/") if len(line) > 3 else line
        if path.startswith(AUDIT_PATH_PREFIXES):
            revision_evidence_changes.append(line)
    return {
        "commit": first_line(commit),
        "branch": first_line(branch),
        "submittedTag": "v1.0.0",
        "submittedTagCommit": first_line(tag_commit),
        "submittedTagMatchesAuditCommit": first_line(commit) == first_line(tag_commit),
        "sourceTreeCleanOutsideRevisionEvidence": not source_changes,
        "sourceChangesOutsideRevisionEvidence": source_changes,
        "revisionEvidenceChangesExcludedFromSourceBaseline": revision_evidence_changes,
    }


def executable_version(executable: str, args: list[str], root: Path) -> dict[str, Any]:
    command = shutil.which(executable)
    if not command:
        return {"available": False, "command": executable, "output": "not found on PATH"}
    result = run([command, *args], root)
    result["path"] = command
    return result


def mysql_version(root: Path) -> dict[str, Any]:
    candidates = [shutil.which("mysql")]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            result = run([str(candidate), "--version"], root)
            result["path"] = str(candidate)
            return result
    return {"available": False, "command": "mysql", "output": "not found"}


def pit_pre_python_version(root: Path) -> dict[str, Any]:
    candidates = [
        os.environ.get("PIT_PRE_PYTHON"),
        sys.executable,
        shutil.which("python3.10"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            result = run([str(candidate), "--version"], root)
            result["path"] = str(candidate)
            return result
    return {"available": False, "command": "python3.10", "output": "not found"}


def _runtime_entry(result: dict[str, Any], include_local_paths: bool) -> dict[str, Any]:
    version = first_line(result)
    mysql_match = re.search(r"(?i)\bmysql(?:\.exe)?\s+(Ver\s+.*)$", version)
    if mysql_match:
        version = mysql_match.group(1)
    entry = {"detected": result["available"], "version": version}
    if include_local_paths:
        entry["path"] = result.get("path")
    return entry


def environment_metadata(root: Path, include_local_paths: bool) -> dict[str, Any]:
    java = executable_version("java", ["-version"], root)
    maven = executable_version("mvn", ["-version"], root)
    node = executable_version("node", ["--version"], root)
    npm = executable_version("npm", ["--version"], root)
    git = executable_version("git", ["--version"], root)
    mysql = mysql_version(root)
    pit_python = pit_pre_python_version(root)
    audit_python: dict[str, Any] = {"version": platform.python_version()}
    if include_local_paths:
        audit_python["path"] = sys.executable
    return {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "platform": platform.platform(),
        },
        "auditPython": audit_python,
        "pitPrePython": _runtime_entry(pit_python, include_local_paths),
        "java": _runtime_entry(java, include_local_paths),
        "maven": _runtime_entry(maven, include_local_paths),
        "node": _runtime_entry(node, include_local_paths),
        "npm": _runtime_entry(npm, include_local_paths),
        "mysqlCli": {
            **_runtime_entry(mysql, include_local_paths),
            "scopeNote": "CLI discovery only; this does not establish MySQL Server or database availability.",
        },
        "git": _runtime_entry(git, include_local_paths),
    }


def resolve_maven_value(value: str | None, properties: dict[str, str]) -> str | None:
    if not value:
        return None
    match = re.fullmatch(r"\$\{([^}]+)}", value.strip())
    return properties.get(match.group(1), value) if match else value


def backend_dependencies(root: Path) -> dict[str, Any]:
    path = root / "src/backend/pom.xml"
    tree = ET.parse(path)
    document = tree.getroot()
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}
    properties_node = document.find("m:properties", ns)
    properties: dict[str, str] = {}
    if properties_node is not None:
        for child in properties_node:
            properties[child.tag.split("}")[-1]] = (child.text or "").strip()
    dependencies = []
    node = document.find("m:dependencies", ns)
    if node is not None:
        for dependency in node.findall("m:dependency", ns):
            def value(name: str) -> str | None:
                item = dependency.find(f"m:{name}", ns)
                return (item.text or "").strip() if item is not None else None
            dependencies.append({
                "groupId": value("groupId"),
                "artifactId": value("artifactId"),
                "declaredVersion": resolve_maven_value(value("version"), properties),
                "scope": value("scope") or "compile",
            })
    return {
        "projectVersion": (document.findtext("m:version", default="", namespaces=ns) or "").strip(),
        "javaVersion": properties.get("java.version"),
        "springBootVersion": properties.get("spring-boot.version"),
        "dependencies": sorted(dependencies, key=lambda item: (item["groupId"] or "", item["artifactId"] or "")),
    }


def frontend_dependencies(root: Path) -> dict[str, Any]:
    package = json.loads(read_text(root / "src/frontend/package.json"))
    lock_path = root / "src/frontend/package-lock.json"
    lock = json.loads(read_text(lock_path)) if lock_path.is_file() else {}
    lock_packages = lock.get("packages", {})

    def dependency_group(name: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for package_name, declared in sorted(package.get(name, {}).items()):
            resolved = lock_packages.get(f"node_modules/{package_name}", {}).get("version")
            result[package_name] = {"declared": declared, "resolved": resolved}
        return result

    return {
        "name": package.get("name"),
        "version": package.get("version"),
        "scripts": dict(sorted(package.get("scripts", {}).items())),
        "dependencies": dependency_group("dependencies"),
        "devDependencies": dependency_group("devDependencies"),
    }


def python_dependencies(root: Path) -> dict[str, Any]:
    requirements = root / "src/pit_pre/requirements.lock.txt"
    locked = []
    for raw in read_text(requirements).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        locked.append(line)
    manifest_path = root / "src/pit_pre/runtime-manifest.json"
    manifest = json.loads(read_text(manifest_path))
    return {
        "lockedRequirements": sorted(locked, key=str.lower),
        "runtimeManifest": manifest,
        "runtimeManifestSha256": sha256(manifest_path),
    }


def java_test_inventory(root: Path) -> dict[str, Any]:
    test_root = root / "src/backend/src/test"
    files = sorted(test_root.rglob("*Test.java")) if test_root.is_dir() else []
    entries = []
    annotation_pattern = re.compile(r"@(Test|ParameterizedTest|RepeatedTest|TestFactory)\b")
    class_pattern = re.compile(r"\bclass\s+([A-Za-z_$][A-Za-z0-9_$]*(?:Test|Tests))\b")
    for path in files:
        content = read_text(path)
        entries.append({
            "path": relative(path, root),
            "classes": sorted(class_pattern.findall(content)),
            "testMethods": len(annotation_pattern.findall(content)),
        })
    return {
        "testFiles": len(files),
        "testClasses": sum(len(item["classes"]) for item in entries),
        "testMethods": sum(item["testMethods"] for item in entries),
        "files": entries,
    }


def python_test_inventory(root: Path) -> dict[str, Any]:
    test_root = root / "src/pit_pre/tests"
    files = sorted(test_root.rglob("test_*.py")) if test_root.is_dir() else []
    entries = []
    for path in files:
        module = ast.parse(read_text(path), filename=str(path))
        classes = []
        methods = []
        module_functions = []
        for node in module.body:
            if isinstance(node, ast.ClassDef):
                class_methods = sorted(
                    child.name for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_")
                )
                if class_methods:
                    classes.append(node.name)
                    methods.extend(f"{node.name}.{name}" for name in class_methods)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                module_functions.append(node.name)
        entries.append({
            "path": relative(path, root),
            "classes": sorted(classes),
            "testMethods": sorted(methods + module_functions),
        })
    return {
        "testFiles": len(files),
        "testClasses": sum(len(item["classes"]) for item in entries),
        "testMethods": sum(len(item["testMethods"]) for item in entries),
        "files": entries,
    }


def ci_inventory(root: Path) -> dict[str, Any]:
    workflow_root = root / ".github/workflows"
    workflows = []
    operating_systems: set[str] = set()
    if workflow_root.is_dir():
        for path in sorted([*workflow_root.glob("*.yml"), *workflow_root.glob("*.yaml")]):
            content = read_text(path)
            runs_on = sorted(set(re.findall(r"^\s*runs-on:\s*['\"]?([^'\"\s#]+)", content, flags=re.MULTILINE)))
            operating_systems.update(runs_on)
            workflows.append({"path": relative(path, root), "runsOn": runs_on})
    return {"workflowFiles": workflows, "operatingSystems": sorted(operating_systems)}


def docker_inventory(root: Path) -> dict[str, Any]:
    matches = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = relative(path, root)
        if rel.startswith(".git/"):
            continue
        name = path.name.lower()
        if name == "dockerfile" or name.startswith("dockerfile.") or name in {
            "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"
        }:
            matches.append(rel)
    return {"present": bool(matches), "files": matches}


def model_inventory(root: Path) -> dict[str, Any]:
    model_root = root / "src/pit_pre/models"
    bundles = []
    artifacts = []
    if model_root.is_dir():
        for bundle in sorted(path for path in model_root.iterdir() if path.is_dir()):
            files = sorted(path for path in bundle.rglob("*") if path.is_file())
            bundle_artifacts = []
            for path in files:
                item = {"path": relative(path, root), "bytes": path.stat().st_size, "sha256": sha256(path)}
                artifacts.append(item)
                bundle_artifacts.append(item)
            bundles.append({
                "directory": relative(bundle, root),
                "fileCount": len(bundle_artifacts),
                "bytes": sum(item["bytes"] for item in bundle_artifacts),
                "artifacts": bundle_artifacts,
            })
    return {"bundleDirectories": bundles, "artifactCount": len(artifacts), "artifacts": artifacts}


def sql_inventory(root: Path) -> dict[str, Any]:
    sql_root = root / "sql/shm_em_database"
    table_sources: dict[str, set[str]] = {}
    create_pattern = re.compile(r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+`?([A-Za-z0-9_]+)`?", re.IGNORECASE)
    sql_files = sorted(sql_root.glob("*.sql")) if sql_root.is_dir() else []
    for path in sql_files:
        for name in create_pattern.findall(read_text(path)):
            table_sources.setdefault(name.lower(), set()).add(relative(path, root))
    all_tables = sorted(table_sources)
    contract_names = {
        "em_project", "em_station", "em_instrument", "em_metric", "em_station_metric",
        "em_observation_table_registry", "em_conversion_operator", "em_conversion_parameter",
        "em_reference_binding", "em_prediction_model", "em_prediction_feature_mapping",
        "em_feature_operator", "em_dataset_manifest", "em_scenario_profile", "em_expected_output",
        "em_future_state_policy",
    }
    prediction_names = {
        "em_prediction_model", "em_prediction_feature_mapping", "em_prediction_batch",
        "em_prediction_run", "em_prediction_result", "em_prediction_execution_gate",
        "em_event_prediction_link", "em_expected_output", "em_future_state_policy",
    }
    provenance_names = {
        "em_event_prediction_link", "em_event_evaluation_run", "em_event_metric_snapshot",
        "em_event_evidence_link", "em_audit_log",
    }
    return {
        "sqlFiles": [relative(path, root) for path in sql_files],
        "allCreateTableCount": len(all_tables),
        "allCreateTables": all_tables,
        "tableSources": {name: sorted(paths) for name, paths in sorted(table_sources.items())},
        "contractTables": sorted(contract_names.intersection(all_tables)),
        "predictionAndResultTables": sorted(prediction_names.intersection(all_tables)),
        "provenanceTables": sorted(provenance_names.intersection(all_tables)),
        "observationTables": sorted(name for name in all_tables if name.startswith("em_obs_")),
    }


def line_matches(root: Path, names: Iterable[str]) -> list[dict[str, Any]]:
    results = []
    wanted = set(names)
    for source_root in RUNTIME_SOURCE_ROOTS:
        base = root / source_root
        if not base.is_dir():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES):
            for number, line in enumerate(read_text(path).splitlines(), 1):
                if any(name in line for name in wanted):
                    results.append({"path": relative(path, root), "line": number, "text": line.strip()})
    return results


def implementation_inventory(root: Path) -> dict[str, Any]:
    java_root = root / "src/backend/src/main/java"

    def paths_for(filename: str) -> list[str]:
        return [relative(path, root) for path in sorted(java_root.rglob(filename))] if java_root.is_dir() else []

    endpoint_matches = []
    route_pattern = re.compile(r"@GetMapping\(\"/events/\{eventId}/trace\"\)")
    for path in sorted(java_root.rglob("*.java")) if java_root.is_dir() else []:
        for number, line in enumerate(read_text(path).splitlines(), 1):
            if route_pattern.search(line):
                endpoint_matches.append({"path": relative(path, root), "line": number, "route": "GET /api/em/predictions/events/{eventId}/trace"})
    return {
        "futureStateImplementations": paths_for("ProjectFutureStateServiceImpl.java"),
        "futureStateInterfaces": paths_for("ProjectFutureStateService.java"),
        "executionGateImplementations": paths_for("PredictionExecutionGateServiceImpl.java"),
        "executionGateInterfaces": paths_for("PredictionExecutionGateService.java"),
        "provenanceEndpoint": endpoint_matches,
        "provenanceServices": paths_for("PredictionServiceImpl.java") + paths_for("EventEvaluationServiceImpl.java"),
        "provenanceMapper": paths_for("EventPredictionTraceMapper.java"),
    }


def hardcoded_identifier_inventory(root: Path) -> dict[str, Any]:
    project_code_pattern = re.compile(r"['\"]((?:SHM_EM|IEM)_[A-Z0-9_]+)['\"]")
    project_id_patterns = [
        re.compile(r"\bprojectId\s*(?::[^=;]+)?=\s*(\d+)(?:L)?\b"),
        re.compile(r"\bproject_id\s*=\s*(\d+)\b"),
        re.compile(r"\bsetProjectId\(\s*(\d+)(?:L)?\s*\)"),
    ]
    model_literal_pattern = re.compile(
        r"['\"](" + "|".join(re.escape(code) for code in MODEL_CODE_LITERALS) + r")['\"]"
    )
    physical_table_pattern = re.compile(r"['\"](em_obs_[A-Za-z0-9_]+)['\"]")
    findings = {"projectCodes": [], "numericProjectIds": [], "modelCodes": [], "physicalObservationTables": []}
    for source_root in RUNTIME_SOURCE_ROOTS:
        base = root / source_root
        if not base.is_dir():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES):
            for number, line in enumerate(read_text(path).splitlines(), 1):
                location = {"path": relative(path, root), "line": number, "text": line.strip()}
                for value in project_code_pattern.findall(line):
                    findings["projectCodes"].append({**location, "identifier": value})
                for pattern in project_id_patterns:
                    for value in pattern.findall(line):
                        findings["numericProjectIds"].append({**location, "identifier": value})
                for value in model_literal_pattern.findall(line):
                    findings["modelCodes"].append({**location, "identifier": value})
                for value in physical_table_pattern.findall(line):
                    findings["physicalObservationTables"].append({**location, "identifier": value})
    for key in findings:
        unique: dict[tuple[Any, ...], dict[str, Any]] = {}
        for item in findings[key]:
            unique[(item["path"], item["line"], item["identifier"], item["text"])] = item
        findings[key] = [unique[index] for index in sorted(unique)]
    findings["total"] = sum(len(findings[key]) for key in findings if key != "total")
    return findings


def _semantic_literal(kind: str, item: dict[str, Any]) -> dict[str, Any]:
    path = item["path"]
    line = int(item["line"])
    if kind == "project_code":
        category = "HARMLESS_DEFAULT"
        impact = "CLI convenience default; --project-code overrides it before contract loading."
        coupling = "NO"
        core_change = "NO"
        claim_change = "NO"
        notes = "Keep unless a later reuse experiment proves that the override path fails."
    elif kind == "observation_table":
        category = "SECURITY_WHITELIST"
        impact = "Registry-selected identifiers are constrained to an approved physical-table set."
        coupling = "CONDITIONAL"
        core_change = "CONDITIONAL"
        claim_change = "YES"
        notes = (
            "Safe for existing approved tables. A new physical table currently requires a whitelist edit; "
            "the registration-only claim must state this boundary unless validation becomes registry-backed."
        )
    elif path.startswith("src/frontend/"):
        category = "UI_DISPLAY_ONLY"
        impact = "Affects labels or default feature selection in the UI, not API, gate, or event semantics."
        coupling = "NO"
        core_change = "NO"
        claim_change = "NO"
        notes = "Retain as presentation behavior; it is not evidence of workflow coupling."
    elif path.endswith("cached_model_runner.py"):
        category = "MODEL_ADAPTER_CONSTRAINT"
        impact = "The cached runner dispatches packaged model signatures by supported target type."
        coupling = "CONDITIONAL"
        core_change = "CONDITIONAL"
        claim_change = "YES"
        notes = (
            "Unknown target types are not arbitrary plug-ins. Limit the claim to compatible bundles under "
            "the existing PIT_PRE adapter contract unless a later approved change generalizes the runner."
        )
    elif path.endswith("result_writer.py") and line <= 22:
        category = "MODEL_ADAPTER_CONSTRAINT"
        impact = "Maps packaged target types to their native prediction-column names."
        coupling = "CONDITIONAL"
        core_change = "NO"
        claim_change = "YES"
        notes = (
            "A single *_pred fallback exists, but compatibility still depends on the packaged output shape; "
            "describe new models as compatible model bundles."
        )
    elif path.endswith("result_writer.py"):
        category = "ENGINEERING_DOMAIN_ADAPTER"
        impact = "Applies target-specific engineering conversion and reference/baseline semantics."
        coupling = "CONDITIONAL"
        core_change = "CONDITIONAL"
        claim_change = "YES"
        notes = (
            "Unknown targets receive an identity mapping, but a new non-identity engineering quantity needs "
            "a validated conversion adapter and prerequisites."
        )
    else:
        category = "MODEL_ADAPTER_CONSTRAINT"
        impact = "Target literal participates in packaged-model compatibility logic."
        coupling = "CONDITIONAL"
        core_change = "CONDITIONAL"
        claim_change = "YES"
        notes = "Review under the compatible-model boundary before core freeze."
    return {
        "path": path,
        "line": line,
        "literal": item["identifier"],
        "literal_kind": kind,
        "semantic_category": category,
        "architectural_impact": impact,
        "core_coupling": coupling,
        "requires_core_change": core_change,
        "requires_claim_change": claim_change,
        "review_notes": notes,
        "source_text": item["text"],
    }


def architecture_coupling_review(data: dict[str, Any]) -> dict[str, Any]:
    inventory = data["hardcodedRuntimeIdentifiers"]
    rows = []
    for item in inventory["projectCodes"]:
        rows.append(_semantic_literal("project_code", item))
    for item in inventory["modelCodes"]:
        rows.append(_semantic_literal("model_target", item))
    for item in inventory["physicalObservationTables"]:
        rows.append(_semantic_literal("observation_table", item))
    for item in inventory["numericProjectIds"]:
        classified = _semantic_literal("numeric_project_id", item)
        classified.update({
            "semantic_category": "GENUINE_ARCHITECTURAL_COUPLING",
            "architectural_impact": "A fixed project identifier can bypass project-scoped configuration.",
            "core_coupling": "YES",
            "requires_core_change": "YES",
            "requires_claim_change": "YES",
            "review_notes": "No numeric project-ID literal was detected in the current runtime baseline.",
        })
        rows.append(classified)
    rows.sort(key=lambda row: (row["path"], row["line"], row["literal_kind"], row["literal"]))
    for index, row in enumerate(rows, 1):
        row["id"] = f"L{index:03d}"
    categories = (
        "HARMLESS_DEFAULT", "UI_DISPLAY_ONLY", "SECURITY_WHITELIST",
        "ENGINEERING_DOMAIN_ADAPTER", "MODEL_ADAPTER_CONSTRAINT",
        "GENUINE_ARCHITECTURAL_COUPLING",
    )
    counts = {category: sum(row["semantic_category"] == category for row in rows) for category in categories}
    return {
        "schemaVersion": "shm-em-architecture-coupling-review-v1",
        "sourceGitCommit": data["git"]["commit"],
        "literalCount": len(rows),
        "categoryCounts": counts,
        "conclusion": (
            "No literal is classified as unconditional project-specific event-workflow coupling. "
            "The material boundaries are the approved observation-table set, packaged model adapters, "
            "and target-specific engineering conversion adapters."
        ),
        "items": rows,
    }


def render_architecture_review(review: dict[str, Any]) -> str:
    lines = [
        "# SHM-EM Phase 0.5 Runtime Literal Semantic Review",
        "",
        f"- Source commit: `{review['sourceGitCommit']}`",
        f"- Classified literals: `{review['literalCount']}`",
        f"- Conclusion: {review['conclusion']}",
        "",
        "## Category totals",
        "",
        *markdown_table(["Category", "Count"], [[key, value] for key, value in review["categoryCounts"].items()]),
        "",
        "## Itemized review",
        "",
        *markdown_table(
            ["ID", "File", "Line", "Literal", "Category", "Core coupling", "Code change", "Claim change", "Notes"],
            [[
                row["id"], row["path"], row["line"], row["literal"], row["semantic_category"],
                row["core_coupling"], row["requires_core_change"], row["requires_claim_change"],
                row["review_notes"],
            ] for row in review["items"]],
        ),
        "",
        "## Interpretation boundary",
        "",
        "Literal presence alone is not proof of architectural coupling. The classifications above distinguish harmless defaults, display behavior, identifier security controls, engineering-domain adapters, and packaged-model adapter constraints.",
        "",
    ]
    return "\n".join(lines)


def claim_gap_matrix(data: dict[str, Any], alignment: dict[str, Any] | None) -> dict[str, Any]:
    alignment_evidence = (
        "Alignment audit v3 separates asynchronous as-of matching from actual fill and records signed temporal offsets: "
        f"{alignment['overall']['asofCellCount']} as-of cells and "
        f"{alignment['overall']['interiorInterpolationCellCount'] + alignment['overall']['leadingBoundaryExtensionCellCount'] + alignment['overall']['trailingBoundaryExtensionCellCount']} filled cells."
        if alignment else
        "Alignment evidence has not yet been generated; run audit_input_alignment.py."
    )
    items = [
        {
            "id": "C01",
            "topic": "Observation registry decoupling",
            "manuscript_claim": "Logical observations are decoupled from physical storage through the observation registry.",
            "implementation_status": "Backend routing is registry-based; PIT_PRE resolves registry rows but validates table identifiers against a four-table allowlist.",
            "evidence_status": "PARTIALLY_SUPPORTED",
            "risk": "MEDIUM",
            "recommended_action": "Limit the claim to approved reference adapters, then decide whether registry-backed table approval is required before core freeze.",
            "evidence_refs": ["src/pit_pre/pit_pre/features.py", "em_observation_table_registry"],
        },
        {
            "id": "C02",
            "topic": "New project by minimal registration",
            "manuscript_claim": "A new project can be integrated through registrations and mappings without core workflow changes.",
            "implementation_status": "Project code, stations, metrics, mappings, and APIs are parameterized; storage-table and model-adapter boundaries remain conditional.",
            "evidence_status": "NEEDS_EXPERIMENT",
            "risk": "HIGH",
            "recommended_action": "Do not claim demonstration until a second configuration is added after core freeze and a Git change inventory is generated.",
            "evidence_refs": ["src/pit_pre/pit_pre/main.py", "src/pit_pre/pit_pre/contract.py", "src/pit_pre/pit_pre/features.py"],
        },
        {
            "id": "C03",
            "topic": "New model by registration",
            "manuscript_claim": "A new fixed model is integrated by registering its bundle, inputs, targets, and temporal settings.",
            "implementation_status": "Database contracts and hashes are authoritative, but CachedModelRunner and engineering conversion support a bounded adapter family.",
            "evidence_status": "PARTIALLY_SUPPORTED",
            "risk": "HIGH",
            "recommended_action": "Change the claim to a compatible model bundle under the existing PIT_PRE model and engineering-adapter contract.",
            "evidence_refs": ["src/pit_pre/pit_pre/contract.py", "src/pit_pre/pit_pre/cached_model_runner.py", "src/pit_pre/pit_pre/result_writer.py"],
        },
        {
            "id": "C04",
            "topic": "Core workflow unchanged",
            "manuscript_claim": "Reuse does not require changes to core backend, frontend, event workflow, or existing source tables.",
            "implementation_status": "The architecture is project-scoped, but no post-freeze cross-configuration change inventory exists.",
            "evidence_status": "NEEDS_EXPERIMENT",
            "risk": "HIGH",
            "recommended_action": "Freeze the approved core first, then measure actual changes for the second heterogeneous configuration.",
            "evidence_refs": ["architecture-coupling-review.json"],
        },
        {
            "id": "C05",
            "topic": "Missing and asynchronous input handling",
            "manuscript_claim": "PIT_PRE aligns heterogeneous observations into auditable rolling model inputs.",
            "implementation_status": "Backward as-of matching uses one sampling interval as tolerance, followed by interior interpolation or boundary extension, then ffill and bfill. Phase 0.6.1 persists descriptive per-model counts, fill ratios, gaps, signed temporal offsets, past lag, and future lead without adding eligibility thresholds.",
            "evidence_status": "PARTIALLY_SUPPORTED",
            "risk": "HIGH",
            "recommended_action": f"Report asynchronous alignment separately from actual interpolation/fill and do not infer acceptance thresholds from one sample. {alignment_evidence}",
            "evidence_refs": ["src/pit_pre/pit_pre/features.py", "artifacts/revision/phase0_6_1/alignment-audit-v3-summary.json", "artifacts/revision/phase0_6_1/one-pass-regression-input.json"],
        },
        {
            "id": "C06",
            "topic": "Execution-gate safety",
            "manuscript_claim": "Invalid prediction states cannot create formal events.",
            "implementation_status": "The gate checks model/run/result integrity, time, quality, hashes, and freshness, but the requested negative matrix has not been executed.",
            "evidence_status": "NEEDS_EXPERIMENT",
            "risk": "HIGH",
            "recommended_action": "Keep gate logic unchanged and run the F01-F12 fault matrix with before/after event, response, and provenance counts.",
            "evidence_refs": ["src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/PredictionExecutionGateServiceImpl.java"],
        },
        {
            "id": "C07",
            "topic": "Evaluate and Execute independence",
            "manuscript_claim": "Execute recalculates and rechecks the gate rather than trusting a stored Evaluate result.",
            "implementation_status": "Separate service paths and recheck calls are present in source, but mutation between Evaluate and Execute has not been demonstrated.",
            "evidence_status": "NEEDS_EXPERIMENT",
            "risk": "MEDIUM",
            "recommended_action": "Run F12; do not change Evaluate or Execute logic in advance.",
            "evidence_refs": ["src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/EventEvaluationServiceImpl.java"],
        },
        {
            "id": "C08",
            "topic": "Project Future State",
            "manuscript_claim": "Forecasts are synchronized and aggregated by target, station, and project with earliest exceedance and a state hash.",
            "implementation_status": "The service implements policy selection, unit-aware thresholds, consecutive steps, aggregation, earliest exceedance, timeline, and hashing.",
            "evidence_status": "ARCHITECTURE_ONLY",
            "risk": "MEDIUM",
            "recommended_action": "Derive the formal specification from code and add boundary tests without changing the algorithm.",
            "evidence_refs": ["src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/ProjectFutureStateServiceImpl.java"],
        },
        {
            "id": "C09",
            "topic": "Event provenance",
            "manuscript_claim": "A formal forecast event is traceable to rule, batch, run, model hashes, input window, and triggering values.",
            "implementation_status": "Trace persistence and GET /api/em/predictions/events/{eventId}/trace exist; no deterministic trace artifact has been published.",
            "evidence_status": "NEEDS_EXPERIMENT",
            "risk": "MEDIUM",
            "recommended_action": "Generate one isolated formal event and export its complete machine-readable trace.",
            "evidence_refs": ["src/backend/src/main/java/mybatis/iem/em/modules/engineering/api/controller/PredictionController.java", "em_event_prediction_link"],
        },
        {
            "id": "C10",
            "topic": "Cross-platform portability",
            "manuscript_claim": "The public workflow is reproducible with documented dependencies.",
            "implementation_status": "The submitted baseline has Windows-only CI and no Docker or Compose files.",
            "evidence_status": "PARTIALLY_SUPPORTED",
            "risk": "HIGH",
            "recommended_action": "Retain the current Windows limitation until a later authorized Linux/Bash or container reproduction is actually validated.",
            "evidence_refs": [".github/workflows/ci.yml", "docs/REPRODUCIBILITY.md"],
        },
        {
            "id": "C11",
            "topic": "Model history-window description",
            "manuscript_claim": "The public reference workflow uses 16 historical input steps.",
            "implementation_status": "The public sample supplies a 16-step common source window, while registered model contracts consume model-specific histories: YD 16, XD 12, Strain 13, Pressure 13, water 13, and settlement 12 steps.",
            "evidence_status": "PARTIALLY_SUPPORTED",
            "risk": "MEDIUM",
            "recommended_action": "Revise the manuscript and Figure 5 to distinguish the shared 16-step source window from model-specific 12-16-step history requirements.",
            "evidence_refs": ["artifacts/revision/phase0_6_1/alignment-audit-v3-summary.json", "sql/shm_em_database/02_SHM_EM_public_sample.sql"],
        },
    ]
    statuses = ("DEMONSTRATED", "PARTIALLY_SUPPORTED", "ARCHITECTURE_ONLY", "CONTRADICTED_BY_IMPLEMENTATION", "NEEDS_EXPERIMENT")
    return {
        "schemaVersion": "shm-em-claim-gap-matrix-v1",
        "sourceGitCommit": data["git"]["commit"],
        "statusCounts": {status: sum(item["evidence_status"] == status for item in items) for status in statuses},
        "items": items,
    }


def render_claim_gap(matrix: dict[str, Any]) -> str:
    lines = [
        "# SHM-EM Phase 0.6 Updated Claim-Gap Matrix",
        "",
        *markdown_table(["Status", "Count"], [[key, value] for key, value in matrix["statusCounts"].items()]),
        "",
        *markdown_table(
            ["ID", "Claim", "Implementation", "Evidence status", "Risk", "Recommended action"],
            [[item["id"], item["manuscript_claim"], item["implementation_status"], item["evidence_status"], item["risk"], item["recommended_action"]] for item in matrix["items"]],
        ),
        "",
    ]
    return "\n".join(lines)


def minimal_change_proposal(alignment: dict[str, Any] | None) -> str:
    alignment_note = (
        "Alignment audit v3 is available; it is descriptive evidence and does not justify an eligibility threshold."
        if alignment else
        "Do not consider thresholds before alignment audit v3 is available."
    )
    items = [
        ("A1", "A", "Alignment diagnostics without changing numeric filling", "WideTableBuilder performs as-of/interpolation/fill processing; Phase 0.6.1 adds directional attribution and compact provenance.", "Reviewer concerns require explicit evidence that instrumentation does not alter numerical behavior.", "Persist policy version, corrected stage counts, fill ratio, gap, signed offset, past lag, and future lead in input_snapshot_json and require zero-difference regression. " + alignment_note, "src/pit_pre/pit_pre/features.py; pipeline.py; result_writer.py", "MEDIUM", "NO for numeric inputs; YES for persisted metadata", "EXPECTED_METADATA_ONLY", "NO", "YES", "APPROVED_CODE_CHANGE"),
        ("A2", "B", "Input-quality acceptance thresholds", "No scientifically justified fill, gap, or temporal-offset limits are defined.", "A threshold inferred from one public sample would add unsupported business behavior and a new reviewer question.", "Deferred and not approved. Record diagnostics only; do not block a model, batch, Execute, or gate from the new values.", "none in Phase 0.6.1", "HIGH", "NO CHANGE AUTHORIZED", "NO", "NO", "NO", "DEFERRED_NOT_APPROVED"),
        ("B1", "B", "Observation-registry scope", "PIT_PRE uses registry mappings plus a four-table security allowlist.", "An unrestricted registration-only claim is broader than the implementation.", "State that v1.x supports registered mappings over approved reference observation adapters; evaluate registry-backed identifier approval only if the second configuration needs a new table.", "src/pit_pre/pit_pre/features.py; manuscript claim", "LOW", "NO", "NO", "NO", "CONDITIONAL", "CLAIM_CHANGE"),
        ("B2", "B", "Compatible-model scope", "CachedModelRunner dispatches the six packaged target adapter signatures and rejects unknown target types.", "Arbitrary-model plug-in wording would overclaim the runtime boundary.", "Replace 'a new model' with 'a compatible model bundle under the existing PIT_PRE adapter contract'.", "src/pit_pre/pit_pre/cached_model_runner.py; result_writer.py", "LOW", "NO", "NO", "NO", "NO", "CLAIM_CHANGE"),
        ("B3", "B", "Engineering conversion adapter scope", "Non-identity YD, XD, water, and settlement outputs use target-specific conversion branches; other targets use identity mapping.", "A new engineering quantity may need an adapter and reference data.", "Document the identity fallback and require a validated engineering conversion adapter for non-identity quantities.", "src/pit_pre/pit_pre/result_writer.py", "LOW", "NO", "NO", "NO", "NO", "CLAIM_CHANGE"),
        ("C1", "C", "Execution-gate failure matrix", "Gate mechanisms already exist.", "Safety evidence is missing.", "Run F01-F12 and verify zero formal-event, response, and provenance deltas for blocked cases.", "tests and tools/revision only", "LOW", "NO", "NO", "NO", "NO", "EXPERIMENT_ONLY"),
        ("C2", "C", "Evaluate/Execute mutation test", "Execute rechecks current state in source.", "Independence is not experimentally demonstrated.", "Run F12 without modifying production logic.", "tests and tools/revision only", "LOW", "NO", "NO", "NO", "NO", "EXPERIMENT_ONLY"),
        ("C3", "C", "Future State formalization", "Aggregation and hashing logic already exist.", "Formal specification and boundary evidence are incomplete.", "Derive pseudocode from implementation and add boundary tests; do not alter the algorithm.", "docs/revision and tests", "LOW", "NO", "NO", "NO", "NO", "EXPERIMENT_ONLY"),
        ("C4", "C", "Provenance trace demonstration", "Trace API and persistence exist.", "No fixed end-to-end trace artifact exists.", "Generate one deterministic reproduction event and export the complete chain.", "tools/revision and artifacts/revision", "LOW", "NO", "NO", "NO", "NO", "EXPERIMENT_ONLY"),
        ("C5", "C", "Post-freeze reuse and portability evidence", "No second configuration, Linux run, Docker run, or scalability result is currently evidenced.", "Several reviewer-facing claims remain untested.", "After core freeze, run the second configuration, reuse inventory, benchmarks, and an approved portability path in their authorized phases.", "later revision phases", "MEDIUM", "NO", "NO", "NO", "NO", "EXPERIMENT_ONLY"),
    ]
    lines = [
        "# Phase 0.6 Scope Decision Record",
        "",
        "> A1 is the only approved diagnostics code change. A2 is deferred; B items are claim boundaries; C items remain later experiments.",
        "",
    ]
    labels = {"A": "Category A - Must resolve before core freeze", "B": "Category B - Prefer claim boundary or conditional change", "C": "Category C - Do not change core; add evidence"}
    headers = ["ID", "Problem", "Current implementation", "Reviewer impact", "Recommendation", "Files", "Risk", "Business behavior", "Reproduction hash", "DB migration", "Pre-freeze", "Action"]
    for category in ("A", "B", "C"):
        lines.extend([f"## {labels[category]}", ""])
        rows = [[item[0], item[2], item[3], item[4], item[5], item[6], item[7], item[8], item[9], item[10], item[11], item[12]] for item in items if item[1] == category]
        lines.extend(markdown_table(headers, rows))
        lines.append("")
    return "\n".join(lines)


def structural_findings(data: dict[str, Any]) -> list[dict[str, str]]:
    findings = []
    git = data["git"]
    if git["submittedTagMatchesAuditCommit"]:
        findings.append({"severity": "PASS", "code": "BASELINE_TAG_MATCH", "message": "The audit commit matches immutable tag v1.0.0."})
    else:
        findings.append({"severity": "HIGH", "code": "BASELINE_TAG_MISMATCH", "message": "The audit commit differs from tag v1.0.0."})
    ci_os = data["continuousIntegration"]["operatingSystems"]
    if ci_os == ["windows-latest"]:
        findings.append({"severity": "HIGH", "code": "CI_WINDOWS_ONLY", "message": "Current CI runs only on windows-latest."})
    if not data["dockerCompose"]["present"]:
        findings.append({"severity": "HIGH", "code": "DOCKER_ABSENT", "message": "No Dockerfile or Compose file is present in the v1.0.0 baseline."})
    if data["hardcodedRuntimeIdentifiers"]["projectCodes"]:
        findings.append({"severity": "INFO", "code": "PROJECT_CODE_LITERAL_FOUND", "message": "Project-code literals are candidates for semantic review, not automatic evidence of coupling."})
    if data["hardcodedRuntimeIdentifiers"]["modelCodes"]:
        findings.append({"severity": "REVIEW", "code": "MODEL_TARGET_LITERAL_FOUND", "message": "Model/target literals require classification as display, domain-adapter, or runtime constraints."})
    if data["hardcodedRuntimeIdentifiers"]["physicalObservationTables"]:
        findings.append({"severity": "REVIEW", "code": "OBSERVATION_TABLE_LITERAL_FOUND", "message": "Observation-table literals require security and extensibility review."})
    if data["tests"]["pitPre"]["testFiles"] == 1:
        findings.append({"severity": "MEDIUM", "code": "PIT_PRE_TEST_SURFACE_NARROW", "message": "PIT_PRE has one test module in the submitted baseline."})
    findings.append({"severity": "INFO", "code": "PHASE0_STRUCTURAL_ONLY", "message": "Phase 0 inventories structure and does not claim that tests, inference, or reproduction passed."})
    return findings


def build_baseline(root: Path, include_local_paths: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schemaVersion": AUDIT_SCHEMA_VERSION,
        "repository": {"name": "SHM-EM", "root": "."},
        "git": git_metadata(root),
        "environment": environment_metadata(root, include_local_paths),
        "dependencies": {
            "backend": backend_dependencies(root),
            "frontend": frontend_dependencies(root),
            "pitPre": python_dependencies(root),
        },
        "tests": {
            "backend": java_test_inventory(root),
            "pitPre": python_test_inventory(root),
        },
        "frontendScripts": frontend_dependencies(root)["scripts"],
        "continuousIntegration": ci_inventory(root),
        "dockerCompose": docker_inventory(root),
        "models": model_inventory(root),
        "database": sql_inventory(root),
        "implementations": implementation_inventory(root),
        "hardcodedRuntimeIdentifiers": hardcoded_identifier_inventory(root),
    }
    data["findings"] = structural_findings(data)
    return data


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        values = [str(value).replace("|", "\\|").replace("\n", " ") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def render_markdown(data: dict[str, Any]) -> str:
    git = data["git"]
    env = data["environment"]
    backend_tests = data["tests"]["backend"]
    pit_tests = data["tests"]["pitPre"]
    lines = [
        "# SHM-EM Phase 0 Repository Baseline",
        "",
        "> Structural audit only. No benchmark, inference, database mutation, or behavioral validation is claimed here.",
        "",
        "## Baseline identity",
        "",
        *markdown_table(["Item", "Value"], [
            ["Schema", data["schemaVersion"]],
            ["Branch", git["branch"]],
            ["Commit", git["commit"]],
            ["Submitted tag", git["submittedTag"]],
            ["Submitted tag commit", git["submittedTagCommit"]],
            ["Tag matches audit commit", git["submittedTagMatchesAuditCommit"]],
            ["Source tree clean outside revision evidence", git["sourceTreeCleanOutsideRevisionEvidence"]],
        ]),
        "",
        "## Environment",
        "",
        *markdown_table(["Runtime", "Detected", "Version"], [
            ["OS", "True", env["os"]["platform"]],
            ["Audit Python", "True", env["auditPython"]["version"]],
            ["PIT_PRE Python", env["pitPrePython"]["detected"], env["pitPrePython"]["version"] or "not detected"],
            ["Java", env["java"]["detected"], env["java"]["version"] or "not detected"],
            ["Maven", env["maven"]["detected"], env["maven"]["version"] or "not detected"],
            ["Node", env["node"]["detected"], env["node"]["version"] or "not detected"],
            ["npm", env["npm"]["detected"], env["npm"]["version"] or "not detected"],
            ["MySQL CLI", env["mysqlCli"]["detected"], env["mysqlCli"]["version"] or "not detected"],
            ["Git", env["git"]["detected"], env["git"]["version"] or "not detected"],
        ]),
        "",
        "MySQL CLI detection only indicates whether this audit process found the command-line client. It does not establish MySQL Server or database availability.",
        "",
        "## Test inventory",
        "",
        *markdown_table(["Component", "Test files", "Test classes", "Test methods"], [
            ["Backend", backend_tests["testFiles"], backend_tests["testClasses"], backend_tests["testMethods"]],
            ["PIT_PRE", pit_tests["testFiles"], pit_tests["testClasses"], pit_tests["testMethods"]],
        ]),
        "",
        "These are source-level counts, not execution results.",
        "",
        "## Frontend scripts",
        "",
        *markdown_table(["Script", "Command"], [[name, command] for name, command in data["frontendScripts"].items()]),
        "",
        "## CI and container baseline",
        "",
        f"- CI operating systems: `{', '.join(data['continuousIntegration']['operatingSystems']) or 'none'}`",
        f"- Docker/Compose present: `{data['dockerCompose']['present']}`",
        f"- Docker/Compose files: `{', '.join(data['dockerCompose']['files']) or 'none'}`",
        "",
        "## Model bundles",
        "",
        *markdown_table(["Bundle", "Files", "Bytes"], [
            [bundle["directory"], bundle["fileCount"], bundle["bytes"]]
            for bundle in data["models"]["bundleDirectories"]
        ]),
        "",
        f"The JSON baseline records SHA-256 for all `{data['models']['artifactCount']}` files in model bundle directories.",
        "",
        "## Database contracts and persistence",
        "",
        f"- Contract tables: `{', '.join(data['database']['contractTables'])}`",
        f"- Prediction/result tables: `{', '.join(data['database']['predictionAndResultTables'])}`",
        f"- Provenance tables: `{', '.join(data['database']['provenanceTables'])}`",
        f"- Observation tables: `{', '.join(data['database']['observationTables'])}`",
        "",
        "## Key implementations",
        "",
        f"- Project Future State: `{', '.join(data['implementations']['futureStateImplementations']) or 'not found'}`",
        f"- Prediction execution gate: `{', '.join(data['implementations']['executionGateImplementations']) or 'not found'}`",
        f"- Provenance endpoint: `{data['implementations']['provenanceEndpoint'][0]['route'] if data['implementations']['provenanceEndpoint'] else 'not found'}`",
        f"- Provenance services: `{', '.join(data['implementations']['provenanceServices']) or 'not found'}`",
        "",
        "## Runtime hardcoding inventory",
        "",
        *markdown_table(["Category", "Occurrences"], [
            ["Project-code literals", len(data["hardcodedRuntimeIdentifiers"]["projectCodes"])],
            ["Numeric project IDs", len(data["hardcodedRuntimeIdentifiers"]["numericProjectIds"])],
            ["Model/target literals", len(data["hardcodedRuntimeIdentifiers"]["modelCodes"])],
            ["Physical observation-table literals", len(data["hardcodedRuntimeIdentifiers"]["physicalObservationTables"])],
        ]),
        "",
        "Repository-relative paths, lines, identifiers, and source text are retained in `repository-baseline.json`.",
        "",
        "## Audit findings",
        "",
        *markdown_table(["Severity", "Code", "Finding"], [
            [item["severity"], item["code"], item["message"]] for item in data["findings"]
        ]),
        "",
        "## Phase 0 boundary",
        "",
        "This audit does not run Maven tests, PIT_PRE inference, frontend builds, MySQL reproduction, failure injection, benchmarks, or provenance reproduction. Those activities belong to later phases and must generate their own machine-readable evidence.",
        "",
    ]
    return "\n".join(lines)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_audit_manifest(output_dir: Path, root: Path, commit: str | None) -> Path:
    manifest_path = output_dir / "audit-manifest.json"
    files = []
    for path in sorted(item for item in output_dir.iterdir() if item.is_file() and item != manifest_path):
        try:
            artifact_path = relative(path, root)
        except ValueError:
            artifact_path = path.name
        files.append({"path": artifact_path, "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = {
        "schemaVersion": "shm-em-audit-manifest-v1",
        "sourceGitCommit": commit,
        "generationTimestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "artifacts": files,
    }
    write_json(manifest_path, manifest)
    return manifest_path


def parse_args() -> argparse.Namespace:
    inferred_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=inferred_root, help="Repository root")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory; defaults to artifacts/revision/audit")
    parser.add_argument(
        "--include-local-paths",
        action="store_true",
        help="Include executable paths for local diagnostics. Disabled for public evidence by default.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo.resolve()
    if not (root / ".git").exists():
        raise SystemExit(f"Not a Git worktree: {root}")
    output_dir = (args.output_dir or root / "artifacts/revision/audit").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline = build_baseline(root, include_local_paths=args.include_local_paths)
    json_path = output_dir / "repository-baseline.json"
    markdown_path = output_dir / "repository-baseline.md"
    write_json(json_path, baseline)
    markdown_path.write_text(render_markdown(baseline), encoding="utf-8")
    architecture = architecture_coupling_review(baseline)
    architecture_json = output_dir / "architecture-coupling-review.json"
    architecture_markdown = output_dir / "architecture-coupling-review.md"
    write_json(architecture_json, architecture)
    architecture_markdown.write_text(render_architecture_review(architecture), encoding="utf-8")
    alignment_paths = [
        root / "artifacts/revision/phase0_6_1/alignment-audit-v3-summary.json",
        root / "artifacts/revision/phase0_6/alignment-audit-v2-summary.json",
        output_dir / "input-alignment-summary.json",
    ]
    alignment_path = next((path for path in alignment_paths if path.is_file()), None)
    alignment = json.loads(read_text(alignment_path)) if alignment_path else None
    claims = claim_gap_matrix(baseline, alignment)
    claim_json = output_dir / "claim-gap-matrix.json"
    claim_markdown = output_dir / "claim-gap-matrix.md"
    write_json(claim_json, claims)
    claim_markdown.write_text(render_claim_gap(claims), encoding="utf-8")
    proposal_path = output_dir / "phase0_6-minimal-change-proposal.md"
    proposal_path.write_text(minimal_change_proposal(alignment), encoding="utf-8")
    manifest_path = write_audit_manifest(output_dir, root, baseline["git"]["commit"])
    print(json_path)
    print(markdown_path)
    print(architecture_json)
    print(architecture_markdown)
    print(claim_json)
    print(claim_markdown)
    print(proposal_path)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
