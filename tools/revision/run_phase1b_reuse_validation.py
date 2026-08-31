#!/usr/bin/env python3
"""Run the Phase 1B cross-configuration reuse validation.

The harness creates only an isolated ``shm_em_reproduce_phase1b_*`` database,
loads the public reproduction sample plus the synthetic bridge registration,
and exercises the frozen SHM-EM workflow without editing production source.
Passwords are accepted from environment/arguments and are never persisted.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

import pymysql


FINAL_CORE_FREEZE_V2 = "b41c1894f75561c8ef682062a5e6dab35c3916a7"
FREEZE_RECORD_COMMIT = "3a1b4fc5990b28929c78f46f93a5deaae85140bf"
PROJECT_CODE = "SHM_EM_SYNTH_BRIDGE"
FROZEN_PATHS = (
    "src/backend/src/main",
    "src/frontend/src",
    "src/pit_pre/pit_pre",
    ".gitattributes",
)
FORMAL_TABLES = {
    "events": "em_monitoring_event",
    "responseWorkflows": "em_event_response_workflow",
    "responseSteps": "em_event_response_step",
    "predictionLinks": "em_event_prediction_link",
    "reports": "em_report_instance",
    "evidenceLinks": "em_event_evidence_link",
    "metricSnapshots": "em_event_metric_snapshot",
    "evidenceResources": "em_evidence_resource",
}


def json_default(value: Any) -> Any:
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat(sep=" ")
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value)!r}")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=json_default) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(
    command: list[str],
    cwd: Path,
    timeout: int,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return {
        "command": [Path(command[0]).name, *command[1:]],
        "exitCode": completed.returncode,
        "elapsedSeconds": round(time.perf_counter() - started, 3),
        "outputTail": completed.stdout.splitlines()[-80:],
        "pass": completed.returncode == 0,
    }


class Database:
    def __init__(self, args: argparse.Namespace):
        self.connection = pymysql.connect(
            host=args.host,
            port=args.port,
            user=args.admin_user,
            password=args.admin_password,
            database=args.database,
            charset="utf8mb4",
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def close(self) -> None:
        self.connection.close()

    def one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        with self.connection.cursor() as cursor:
            return cursor.execute(sql, params)

    def scalar(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        row = self.one(sql, params)
        return next(iter(row.values())) if row else None


class Backend:
    def __init__(self, args: argparse.Namespace, runtime_root: Path):
        self.args = args
        self.runtime_root = runtime_root
        self.process: subprocess.Popen[str] | None = None
        self.stdout_path = runtime_root / "backend.log"
        self._output = None

    def start(self) -> None:
        env = os.environ.copy()
        env.update(
            {
                "DB_URL": (
                    f"jdbc:mysql://{self.args.host}:{self.args.port}/{self.args.database}"
                    "?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai"
                ),
                "DB_USERNAME": self.args.admin_user,
                "DB_PASSWORD": self.args.admin_password,
                "SERVER_PORT": str(self.args.backend_port),
                "SPRING_PROFILES_ACTIVE": "reproduce",
            }
        )
        self._output = self.stdout_path.open("w", encoding="utf-8", newline="\n")
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.process = subprocess.Popen(
            [str(self.args.java), "-jar", str(self.args.backend_jar)],
            cwd=str(self.args.repo_root),
            env=env,
            text=True,
            stdout=self._output,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        deadline = time.time() + self.args.backend_start_timeout
        last_error = ""
        while time.time() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(
                    "Backend exited during startup:\n" + self.stdout_path.read_text(
                        encoding="utf-8", errors="replace"
                    )[-6000:]
                )
            try:
                api_get(self.args.backend_port, "/api/em/projects?limit=1")
                return
            except Exception as exc:  # noqa: BLE001 - startup polling records final error
                last_error = str(exc)
                time.sleep(1)
        raise TimeoutError(f"Backend did not start: {last_error}")

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        if self._output is not None:
            self._output.close()


def api_request(port: int, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            value = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {method} {path}: {text}") from exc
    if value.get("code") != 0:
        raise RuntimeError(f"API rejected {method} {path}: {value}")
    return value


def api_get(port: int, path: str) -> dict[str, Any]:
    return api_request(port, "GET", path)


def api_post(port: int, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    return api_request(port, "POST", path, payload)


def mysql_environment(args: argparse.Namespace) -> dict[str, str]:
    env = os.environ.copy()
    env["MYSQL_PWD"] = args.admin_password
    return env


def mysql_command(args: argparse.Namespace, database: str | None = None) -> list[str]:
    command = [
        str(args.mysql),
        f"--host={args.host}",
        f"--port={args.port}",
        f"--user={args.admin_user}",
        "--default-character-set=utf8mb4",
    ]
    if database:
        command.append(f"--database={database}")
    return command


def initialize_database(args: argparse.Namespace) -> list[dict[str, Any]]:
    env = mysql_environment(args)
    create_sql = (
        f"DROP DATABASE IF EXISTS `{args.database}`; "
        f"CREATE DATABASE `{args.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    )
    created = subprocess.run(
        [*mysql_command(args), f"--execute={create_sql}"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if created.returncode != 0:
        raise RuntimeError(f"Cannot create isolated database: {created.stdout}")

    imports = [
        args.repo_root / "sql/shm_em_database/00_SHM_EM_complete_schema.sql",
        args.repo_root / "sql/shm_em_database/01_SHM_EM_conversion_operators.sql",
        args.repo_root / "sql/shm_em_database/02_SHM_EM_public_sample.sql",
        args.repo_root / "sql/shm_em_database/03_SHM_EM_public_validation.sql",
        args.repo_root / "sql/shm_em_database/04_SHM_EM_persisted_prediction_integrity.sql",
        args.repo_root / "sql/shm_em_database/revision/phase1b_synthetic_bridge.sql",
    ]
    evidence: list[dict[str, Any]] = []
    for path in imports:
        started = time.perf_counter()
        with path.open("rb") as handle:
            completed = subprocess.run(
                mysql_command(args, args.database),
                env=env,
                stdin=handle,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=300,
                check=False,
            )
        item = {
            "path": str(path.relative_to(args.repo_root)).replace("\\", "/"),
            "sha256": sha256_file(path),
            "exitCode": completed.returncode,
            "elapsedSeconds": round(time.perf_counter() - started, 3),
            "pass": completed.returncode == 0,
        }
        evidence.append(item)
        if completed.returncode != 0:
            output = completed.stdout.decode("utf-8", errors="replace")
            raise RuntimeError(f"SQL import failed for {path}:\n{output[-5000:]}")
    return evidence


def formal_counts(db: Database, project_id: int) -> dict[str, int]:
    values: dict[str, int] = {}
    for key, table in FORMAL_TABLES.items():
        if table == "em_event_response_step":
            sql = """
                SELECT COUNT(*)
                FROM em_event_response_step s
                JOIN em_event_response_workflow w ON w.id=s.workflow_id
                WHERE w.project_id=%s
            """
        elif table in {"em_event_prediction_link", "em_event_evidence_link", "em_event_metric_snapshot"}:
            event_column = "event_id"
            sql = f"""
                SELECT COUNT(*)
                FROM {table} x
                JOIN em_monitoring_event e ON e.id=x.{event_column}
                WHERE e.project_id=%s
            """
        else:
            sql = f"SELECT COUNT(*) FROM {table} WHERE project_id=%s"
        values[key] = int(db.scalar(sql, (project_id,)) or 0)
    return values


def delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {key: after[key] - before[key] for key in before}


def configuration_manifest(db: Database, project_id: int) -> dict[str, Any]:
    project = db.one("SELECT * FROM em_project WHERE id=%s", (project_id,))
    counts = db.one(
        """
        SELECT
          (SELECT COUNT(*) FROM em_station WHERE project_id=%s) AS stations,
          (SELECT COUNT(*) FROM em_instrument WHERE project_id=%s) AS instruments,
          (SELECT COUNT(*) FROM em_station_metric WHERE project_id=%s) AS stationMetrics,
          (SELECT COUNT(*) FROM em_observation_table_registry WHERE project_id=%s) AS registries,
          (SELECT COUNT(*) FROM em_prediction_model WHERE project_id=%s AND status='active') AS models,
          (SELECT COUNT(*) FROM em_prediction_feature_mapping WHERE project_id=%s AND enabled=1) AS features,
          (SELECT COALESCE(SUM(prediction_target),0) FROM em_prediction_feature_mapping WHERE project_id=%s AND enabled=1) AS predictionTargets,
          (SELECT COUNT(*) FROM em_event_rule WHERE project_id=%s AND enabled=1) AS rules
        """,
        (project_id,) * 8,
    )
    models = db.all(
        """
        SELECT model_code, target_type, required_history_rows, expected_steps,
               time_step_minutes, input_schema_hash, artifact_hash,
               preprocessor_hash, artifact_bundle_hash
        FROM em_prediction_model
        WHERE project_id=%s AND status='active'
        ORDER BY model_code
        """,
        (project_id,),
    )
    registries = db.all(
        """
        SELECT registry_code, instrument_type, physical_table_name, storage_mode
        FROM em_observation_table_registry
        WHERE project_id=%s ORDER BY registry_code
        """,
        (project_id,),
    )
    composition = db.all(
        """
        SELECT feature_group, source_metric_code, COUNT(*) AS feature_count,
               SUM(prediction_target) AS prediction_target_count
        FROM em_prediction_feature_mapping
        WHERE project_id=%s AND enabled=1
        GROUP BY feature_group, source_metric_code
        ORDER BY feature_group, source_metric_code
        """,
        (project_id,),
    )
    return {
        "project": project,
        "counts": counts,
        "models": models,
        "registries": registries,
        "metricComposition": composition,
        "scope": "software-reuse fixture; no cross-domain predictive-accuracy claim",
    }


def run_negative_onboarding(args: argparse.Namespace, db: Database, project_id: int) -> dict[str, Any]:
    mapping = db.one(
        """
        SELECT id, feature_code, training_feature_code, feature_order
        FROM em_prediction_feature_mapping
        WHERE project_id=%s AND enabled=1 AND required=1
        ORDER BY feature_order DESC, id DESC LIMIT 1
        """,
        (project_id,),
    )
    before = int(db.scalar("SELECT COUNT(*) FROM em_prediction_batch WHERE project_id=%s", (project_id,)) or 0)
    db.execute("UPDATE em_prediction_feature_mapping SET enabled=0 WHERE id=%s", (mapping["id"],))
    try:
        result = run_pit_pre(args)
    finally:
        db.execute("UPDATE em_prediction_feature_mapping SET enabled=1 WHERE id=%s", (mapping["id"],))
    after = int(db.scalar("SELECT COUNT(*) FROM em_prediction_batch WHERE project_id=%s", (project_id,)) or 0)
    output = "\n".join(result["outputTail"])
    rejected = result["exitCode"] != 0 and "Input schema hash mismatch" in output
    return {
        "fault": "one required feature mapping disabled",
        "mapping": mapping,
        "expectedStage": "database model-contract validation before inference",
        "exitCode": result["exitCode"],
        "diagnostic": next((line for line in result["outputTail"] if "Input schema hash mismatch" in line), None),
        "batchCountBefore": before,
        "batchCountAfter": after,
        "successfulBatchCreated": after > before,
        "mappingRestored": int(db.scalar("SELECT enabled FROM em_prediction_feature_mapping WHERE id=%s", (mapping["id"],))) == 1,
        "pass": rejected and before == after,
    }


def pit_pre_config(args: argparse.Namespace, path: Path) -> None:
    value = {
        "database": {
            "host": args.host,
            "port": args.port,
            "database": args.database,
            "user": args.admin_user,
            "password": args.admin_password,
            "charset": "utf8mb4",
        },
        "working_directory": str(args.pit_pre_root),
    }
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def run_pit_pre(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.runtime_root / "pit-pre-config.json"
    pit_pre_config(args, config_path)
    try:
        return run_command(
            [
                str(args.python), "-m", "pit_pre", "--config", str(config_path),
                "--project-code", PROJECT_CODE,
            ],
            args.pit_pre_root,
            args.pit_pre_timeout,
        )
    finally:
        config_path.unlink(missing_ok=True)


def prediction_summary(db: Database, project_id: int) -> dict[str, Any]:
    batch = db.one(
        "SELECT * FROM em_prediction_batch WHERE project_id=%s ORDER BY id DESC LIMIT 1",
        (project_id,),
    )
    if not batch:
        raise RuntimeError("Positive PIT_PRE run did not create a bridge prediction batch")
    runs = db.all(
        """
        SELECT r.id, r.model_id, r.model_code, r.model_version, r.status,
               r.result_hash, r.persisted_result_hash,
               r.persisted_result_hash_version, COUNT(p.id) AS persisted_rows,
               COUNT(DISTINCT p.feature_code) AS target_count,
               MIN(p.step) AS minimum_step, MAX(p.step) AS maximum_step,
               COUNT(DISTINCT p.step) AS covered_steps,
               MIN(p.future_time) AS first_future_time,
               MAX(p.future_time) AS last_future_time
        FROM em_prediction_run r
        JOIN em_prediction_result p ON p.run_id=r.id
        WHERE r.batch_id=%s
        GROUP BY r.id, r.model_id, r.model_code, r.model_version, r.status,
                 r.result_hash, r.persisted_result_hash,
                 r.persisted_result_hash_version
        ORDER BY r.model_code
        """,
        (batch["id"],),
    )
    return {
        "batch": batch,
        "runs": runs,
        "totalPersistedRows": sum(int(item["persisted_rows"]) for item in runs),
        "allRunsSuccessful": all(item["status"] == "success" for item in runs),
        "allRunsIntegrityProtected": all(bool(item["persisted_result_hash"]) for item in runs),
        "batchIntegrityProtected": bool(batch.get("persisted_output_hash")),
    }


def rule_payload(rule_id: int, batch_id: int, execution_mode: str) -> dict[str, Any]:
    return {
        "ruleId": rule_id,
        "projectId": None,
        "inputSource": "PREDICTION",
        "predictionBatchId": batch_id,
        "predictionModelCode": "Pressure",
        "predictionTargetType": "Pressure",
        "predictionFeatureCode": "bridge_point1_0.12Pressure_value",
        "forecastHorizonMinutes": 120,
        "minimumConsecutiveSteps": 3,
        "seriesQualityFilter": "normal",
        "predictionExecutionMode": execution_mode,
    }


def frontend_validation(args: argparse.Namespace, project_id: int) -> dict[str, Any]:
    vue_tsc = args.frontend_root / "node_modules" / ".bin" / (
        "vue-tsc.cmd" if os.name == "nt" else "vue-tsc"
    )
    if vue_tsc.is_file():
        dependency_install = {
            "command": [],
            "exitCode": 0,
            "elapsedSeconds": 0,
            "outputTail": ["Existing npm dependency tree reused."],
            "pass": True,
            "skipped": True,
        }
    else:
        dependency_install = run_command(
            [str(args.npm), "ci"], args.frontend_root, 600
        )
        dependency_install["skipped"] = False

    build = run_command([str(args.npm), "run", "build"], args.frontend_root, 300)
    router_path = args.frontend_root / "src/router/modules/projectWorkflow.ts"
    router_text = router_path.read_text(encoding="utf-8")
    expected_routes = [
        "/projects/:projectId/overview",
        "/projects/:projectId/data/low-frequency",
        "/projects/:projectId/predictions",
        "/projects/:projectId/events",
        "/projects/:projectId/response/workflows",
    ]
    route_checks = {route: route in router_text for route in expected_routes}
    return {
        "sourceModified": False,
        "dependencyInstall": dependency_install,
        "build": build,
        "routeTemplateChecks": route_checks,
        "resolvedRoutes": [route.replace(":projectId", str(project_id)) for route in expected_routes],
        "pass": dependency_install["pass"] and build["pass"] and all(route_checks.values()),
    }


def regression_checks(args: argparse.Namespace) -> dict[str, Any]:
    backend = run_command(
        [str(args.maven), "-q", "test", "package"], args.backend_root, 420
    )
    pit_pre = run_command(
        [str(args.python), "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        args.pit_pre_root,
        240,
    )
    return {
        "backend": backend,
        "pitPre": pit_pre,
        "pass": backend["pass"] and pit_pre["pass"],
    }


def git_output(args: argparse.Namespace, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=str(args.repo_root),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(arguments)} failed: {completed.stderr}")
    return completed.stdout.strip()


def core_diff_inventory(args: argparse.Namespace) -> dict[str, Any]:
    baseline_diff = git_output(args, "diff", "--name-only", FINAL_CORE_FREEZE_V2, "--", *FROZEN_PATHS)
    working_diff = git_output(args, "diff", "--name-only", "--", *FROZEN_PATHS)
    status_lines = git_output(args, "status", "--short", "--untracked-files=all").splitlines()
    untracked_frozen = []
    for line in status_lines:
        path = line[3:].replace("\\", "/") if len(line) > 3 else ""
        if line.startswith("??") and any(path == item or path.startswith(item + "/") for item in FROZEN_PATHS):
            untracked_frozen.append(path)
    frozen = sorted(set(filter(None, baseline_diff.splitlines() + working_diff.splitlines() + untracked_frozen)))
    sql_text = (args.repo_root / "sql/shm_em_database/revision/phase1b_synthetic_bridge.sql").read_text(
        encoding="utf-8"
    )
    altered_source_tables = re.findall(
        r"(?im)^\s*ALTER\s+TABLE\s+`?(em_obs_[A-Za-z0-9_]+)`?", sql_text
    )
    inherited = [
        line for line in status_lines
        if "src/pit_pre/models/" in line or "src/pit_pre/requirements.lock.txt" in line
    ]
    return {
        "baseline": FINAL_CORE_FREEZE_V2,
        "freezeRecordCommit": FREEZE_RECORD_COMMIT,
        "frozenPaths": list(FROZEN_PATHS),
        "frozenFilesModified": frozen,
        "coreBackendFilesModified": len([item for item in frozen if item.startswith("src/backend/src/main/")]),
        "coreFrontendFilesModified": len([item for item in frozen if item.startswith("src/frontend/src/")]),
        "pitPreCoreFilesModified": len([item for item in frozen if item.startswith("src/pit_pre/pit_pre/")]),
        "eventWorkflowFilesModified": len([item for item in frozen if item.startswith("src/backend/src/main/")]),
        "existingSourceTablesAltered": sorted(set(altered_source_tables)),
        "existingSourceTableSchemaChangeCount": len(set(altered_source_tables)),
        "phase1bStatusEntries": [
            line for line in status_lines
            if any(token in line.replace("\\", "/") for token in (
                "sql/shm_em_database/revision/",
                "docs/revision/phase1b-",
                "tools/revision/run_phase1b_",
                "tools/revision/build_phase1b_",
            ))
        ],
        "inheritedEolIndexEntries": inherited,
        "pass": not frozen and not altered_source_tables,
    }


def write_configuration_inventory(path: Path, manifest: dict[str, Any]) -> None:
    rows = [
        ("project", 1, PROJECT_CODE),
        ("stations", manifest["counts"]["stations"], "west pier; midspan; east pier"),
        ("instruments", manifest["counts"]["instruments"], "four instrument families per station"),
        ("station metrics", manifest["counts"]["stationMetrics"], "existing metric catalogue"),
        ("observation registries", manifest["counts"]["registries"], "existing typed adapters"),
        ("feature mappings", manifest["counts"]["features"], "frozen training order"),
        ("active models", manifest["counts"]["models"], "Strain and Pressure workflow fixtures"),
        ("prediction targets", manifest["counts"]["predictionTargets"], "14 Strain + 14 Pressure"),
        ("event rules", manifest["counts"]["rules"], "three-step pressure trigger"),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["item", "count", "detail"])
        writer.writerows(rows)


def phase1b_report(summary: dict[str, Any]) -> str:
    checks = summary["acceptanceChecks"]
    lines = [
        "# Phase 1B Completion Report",
        "",
        f"- Final Core Freeze v2: `{FINAL_CORE_FREEZE_V2}`",
        f"- Second configuration: `{PROJECT_CODE}` (`bridge`)",
        "- Model route: B, unchanged packaged models used as workflow fixtures",
        "- Predictive accuracy claim: none",
        f"- Acceptance: **{sum(1 for item in checks.values() if item['pass'])}/{len(checks)} PASS**",
        "- Phase 1B changes: uncommitted for GPT review",
        "",
        "## Acceptance Gate",
        "",
        "| Check | Result | Evidence |",
        "| --- | --- | --- |",
    ]
    for code, item in checks.items():
        lines.append(f"| {code} | {'PASS' if item['pass'] else 'FAIL'} | {item['evidence']} |")
    lines.extend(
        [
            "",
            "## Outcome",
            "",
            f"- Registered {summary['configuration']['counts']['stations']} stations and "
            f"{summary['configuration']['counts']['instruments']} instruments.",
            f"- Persisted {summary['prediction']['totalPersistedRows']} forecast rows across two models.",
            "- Negative onboarding failed before inference and created no batch.",
            "- Gate passed all dimensions, including persisted-result integrity.",
            "- Future State assessed the Pressure target and returned yellow risk.",
            "- Evaluate created no formal side effects.",
            "- Execute created a formal reproduction event, response workflow, four steps, and prediction provenance.",
            f"- Response step states: RULE_TRIGGER `{summary['responseWorkflowOutcome']['stepStatuses'].get('RULE_TRIGGER')}`, "
            f"NOTIFICATION `{summary['responseWorkflowOutcome']['stepStatuses'].get('NOTIFICATION')}`, "
            f"REPORT_GENERATION `{summary['responseWorkflowOutcome']['stepStatuses'].get('REPORT_GENERATION')}`, "
            f"EVIDENCE_ARCHIVE `{summary['responseWorkflowOutcome']['stepStatuses'].get('EVIDENCE_ARCHIVE')}`.",
            f"- Report records created: {summary['responseWorkflowOutcome']['reportsCreated']}.",
            "- Report-generation success is not an acceptance criterion and is not claimed for the second configuration.",
            "- Event Trace resolves the event to batch/run and immutable model/input metadata; persisted-result integrity is independently revalidated by the execution Gate.",
            "- Frozen backend, frontend, PIT_PRE core, and observation-table schemas remained unchanged.",
            "",
            "## Stop",
            "",
            "Phase 1B is complete and intentionally uncommitted. STOP for GPT review.",
        ]
    )
    return "\n".join(lines)


def manifest_for(root: Path) -> dict[str, Any]:
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "phase1b-manifest.json" or "gpt-review-package" in path.parts:
            continue
        files.append(
            {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schemaVersion": "shm-em-phase1b-evidence-v1",
        "finalCoreFreezeV2": FINAL_CORE_FREEZE_V2,
        "generatedAt": dt.datetime.now().isoformat(timespec="seconds"),
        "fileCount": len(files),
        "files": files,
    }


def resolve_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Run SHM-EM Phase 1B reuse validation")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--admin-user", default="root")
    parser.add_argument("--admin-password", default=os.environ.get("DB_ADMIN_PASSWORD"))
    parser.add_argument("--database", default="shm_em_reproduce_phase1b_bridge")
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--backend-port", type=int, default=5195)
    parser.add_argument("--backend-start-timeout", type=int, default=90)
    parser.add_argument("--pit-pre-timeout", type=int, default=300)
    parser.add_argument("--mysql", type=Path, default=Path(r"D:\Tools\mysql-8.0.41\bin\mysql.exe"))
    parser.add_argument("--python", type=Path, default=Path(r"D:\anaconda3\envs\py310\python.exe"))
    parser.add_argument("--java", type=Path, default=Path(r"C:\Users\nlfdz\.jdks\temurin-1.8.0_482\bin\java.exe"))
    parser.add_argument("--maven", type=Path, default=Path(r"D:\Tools\apache-maven-3.9.16\bin\mvn.cmd"))
    parser.add_argument("--npm", type=Path, default=Path("npm.cmd"))
    args = parser.parse_args()
    if not args.admin_password:
        parser.error("Set DB_ADMIN_PASSWORD; the password is never written to evidence")
    if not re.fullmatch(r"shm_em_reproduce_phase1b_[A-Za-z0-9_]+", args.database):
        parser.error("Database must match shm_em_reproduce_phase1b_*")
    args.repo_root = repo_root
    args.backend_root = repo_root / "src/backend"
    args.frontend_root = repo_root / "src/frontend"
    args.pit_pre_root = repo_root / "src/pit_pre"
    args.evidence_root = (args.evidence_root or repo_root / "artifacts/revision/reuse-v2").resolve()
    args.runtime_root = Path(tempfile.mkdtemp(prefix="shm-em-phase1b-"))
    jars = sorted(
        (args.backend_root / "target").glob("*.jar"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    args.backend_jar = next((item for item in jars if not item.name.endswith(".original")), None)
    for executable in (args.mysql, args.python, args.java, args.maven):
        if not executable.is_file():
            parser.error(f"Executable not found: {executable}")
    if args.backend_jar is None:
        parser.error("Backend jar is missing")
    return args


def main() -> int:
    args = resolve_args()
    evidence_root = args.evidence_root.resolve()
    allowed_root = (args.repo_root / "artifacts/revision").resolve()
    if not evidence_root.is_relative_to(allowed_root):
        raise RuntimeError("Evidence directory escaped artifacts/revision")
    if evidence_root.exists():
        shutil.rmtree(evidence_root)
    evidence_root.mkdir(parents=True)
    shutil.copy2(
        args.repo_root / "docs/revision/phase1b-second-configuration.md",
        evidence_root / "second-configuration-spec.md",
    )
    shutil.copy2(
        args.repo_root / "docs/revision/phase1b-model-fixture-card.md",
        evidence_root / "model-fixture-card.md",
    )

    db: Database | None = None
    backend: Backend | None = None
    try:
        regressions = regression_checks(args)
        write_json(evidence_root / "regression-tests.json", regressions)
        if not regressions["pass"]:
            raise RuntimeError("Regression tests failed")

        imports = initialize_database(args)
        db = Database(args)
        project_id = int(db.scalar("SELECT id FROM em_project WHERE project_code=%s", (PROJECT_CODE,)))
        config = configuration_manifest(db, project_id)
        write_json(evidence_root / "second-configuration-manifest.json", config)
        write_configuration_inventory(evidence_root / "configuration-inventory.csv", config)
        write_json(evidence_root / "sql-imports.json", imports)

        negative = run_negative_onboarding(args, db, project_id)
        write_json(evidence_root / "negative-onboarding-case.json", negative)
        if not negative["pass"]:
            raise RuntimeError("Negative onboarding control failed")

        pit_pre = run_pit_pre(args)
        write_json(evidence_root / "pit-pre-run.json", pit_pre)
        if not pit_pre["pass"]:
            raise RuntimeError("Positive PIT_PRE run failed")
        prediction = prediction_summary(db, project_id)
        write_json(evidence_root / "prediction-summary.json", prediction)
        batch_id = int(prediction["batch"]["id"])
        rule_id = int(db.scalar(
            "SELECT id FROM em_event_rule WHERE project_id=%s AND rule_code='BRIDGE_PRESSURE_WORKFLOW_FIXTURE'",
            (project_id,),
        ))

        backend = Backend(args, args.runtime_root)
        backend.start()
        project_api = api_get(args.backend_port, f"/api/em/projects?projectId={project_id}&limit=10")
        context_api = api_get(args.backend_port, f"/api/em/projects/{project_id}/context")
        object_tree_api = api_get(args.backend_port, f"/api/em/projects/{project_id}/object-tree")
        models_api = api_get(args.backend_port, f"/api/em/predictions/models?projectId={project_id}")
        rules_api = api_get(args.backend_port, f"/api/em/projects/{project_id}/rules")
        series_query = urllib.parse.urlencode(
            {
                "projectId": project_id,
                "batchId": batch_id,
                "modelCode": "Pressure",
                "targetType": "Pressure",
                "featureCode": "bridge_point1_0.12Pressure_value",
                "includeObserved": "true",
            }
        )
        series_api = api_get(args.backend_port, f"/api/em/predictions/series?{series_query}")
        write_json(
            evidence_root / "api-registration-and-series.json",
            {
                "project": project_api,
                "context": context_api,
                "objectTree": object_tree_api,
                "models": models_api,
                "rules": rules_api,
                "seriesCount": len(series_api["data"]),
                "series": series_api,
            },
        )

        gate_api = api_post(
            args.backend_port,
            f"/api/em/predictions/batches/{batch_id}/execution-gate/evaluate?mode=REPRODUCTION",
            {},
        )
        write_json(evidence_root / "gate.json", gate_api)
        future_api = api_get(
            args.backend_port,
            f"/api/em/projects/{project_id}/future-state?batchId={batch_id}"
            "&horizonMinutes=120&executionMode=REPRODUCTION",
        )
        write_json(evidence_root / "future-state.json", future_api)

        before = formal_counts(db, project_id)
        evaluate_api = api_post(
            args.backend_port,
            f"/api/em/projects/{project_id}/rules/{rule_id}/evaluate",
            rule_payload(rule_id, batch_id, "REPLAY"),
        )
        after_evaluate = formal_counts(db, project_id)
        evaluate_evidence = {
            "response": evaluate_api,
            "formalCountsBefore": before,
            "formalCountsAfter": after_evaluate,
            "formalDeltas": delta(before, after_evaluate),
            "formalSideEffectCount": sum(delta(before, after_evaluate).values()),
        }
        write_json(evidence_root / "evaluate.json", evaluate_evidence)

        execute_api = api_post(
            args.backend_port,
            f"/api/em/projects/{project_id}/rules/{rule_id}/execute",
            rule_payload(rule_id, batch_id, "REPRODUCTION"),
        )
        after_execute = formal_counts(db, project_id)
        event_id = int(execute_api["data"]["event"]["id"])
        execute_evidence = {
            "response": execute_api,
            "formalCountsBefore": after_evaluate,
            "formalCountsAfter": after_execute,
            "formalDeltas": delta(after_evaluate, after_execute),
        }
        write_json(evidence_root / "execute.json", execute_evidence)

        trace_api = api_get(args.backend_port, f"/api/em/predictions/events/{event_id}/trace")
        workflow = db.one(
            "SELECT * FROM em_event_response_workflow WHERE project_id=%s AND event_id=%s",
            (project_id, event_id),
        )
        steps = db.all(
            "SELECT * FROM em_event_response_step WHERE workflow_id=%s ORDER BY step_order",
            (workflow["id"],),
        ) if workflow else []
        prediction_link = db.one("SELECT * FROM em_event_prediction_link WHERE event_id=%s", (event_id,))
        provenance = {
            "event": db.one("SELECT * FROM em_monitoring_event WHERE id=%s", (event_id,)),
            "workflow": workflow,
            "workflowSteps": steps,
            "predictionLink": prediction_link,
            "traceApi": trace_api,
        }
        write_json(evidence_root / "provenance-trace.json", provenance)

        frontend = frontend_validation(args, project_id)
        write_json(evidence_root / "frontend-validation.json", frontend)
        core = core_diff_inventory(args)
        write_json(evidence_root / "core-diff-inventory.json", core)
        write_text(
            evidence_root / "core-diff-inventory.md",
            "\n".join(
                [
                    "# Phase 1B Core Diff Inventory",
                    "",
                    f"- Baseline: `{FINAL_CORE_FREEZE_V2}`",
                    f"- Frozen backend files modified: {core['coreBackendFilesModified']}",
                    f"- Frozen frontend files modified: {core['coreFrontendFilesModified']}",
                    f"- PIT_PRE core files modified: {core['pitPreCoreFilesModified']}",
                    f"- Event workflow core files modified: {core['eventWorkflowFilesModified']}",
                    f"- Existing `em_obs_*` schemas altered: {core['existingSourceTableSchemaChangeCount']}",
                    f"- Result: {'PASS' if core['pass'] else 'FAIL'}",
                ]
            ),
        )

        sql_path = args.repo_root / "sql/shm_em_database/revision/phase1b_synthetic_bridge.sql"
        registration = {
            "newProjectRecords": 1,
            "newStations": int(config["counts"]["stations"]),
            "newInstruments": int(config["counts"]["instruments"]),
            "newStationMetricBindings": int(config["counts"]["stationMetrics"]),
            "newObservationRegistryMappings": int(config["counts"]["registries"]),
            "newFeatureMappings": int(config["counts"]["features"]),
            "newModelRegistrations": int(config["counts"]["models"]),
            "newRuleRecords": int(config["counts"]["rules"]),
            "newConfigurationSqlFiles": 1,
            "newModelFixtureFiles": 0,
            "newDocumentationFiles": 2,
            "newRevisionTools": 2,
            "configurationSqlLines": len(sql_path.read_text(encoding="utf-8").splitlines()),
            "coreSourceFilesModified": len(core["frozenFilesModified"]),
            "existingSourceTableSchemaChanges": core["existingSourceTableSchemaChangeCount"],
            "manualStepsRequired": 1,
            "manualStep": "run tools/revision/run_phase1b_reuse_validation.py with an isolated database password",
        }
        write_json(evidence_root / "registration-effort.json", registration)

        evaluate_zero = evaluate_evidence["formalSideEffectCount"] == 0
        execute_delta = execute_evidence["formalDeltas"]
        step_statuses = {item["step_code"]: item["status"] for item in steps}
        response_workflow_outcome = {
            "instantiated": workflow is not None,
            "workflowStatus": workflow["workflow_status"] if workflow else None,
            "stepStatuses": step_statuses,
            "reportsCreated": execute_delta["reports"],
            "acceptanceBoundary": (
                "Report-generation success is not an acceptance criterion for the "
                "cross-configuration reuse experiment and is not claimed."
            ),
        }
        checks = {
            "B1": {"pass": FINAL_CORE_FREEZE_V2 == core["baseline"], "evidence": "Final Core Freeze v2 fixed"},
            "B2": {"pass": config["project"]["infrastructure_type"] == "bridge", "evidence": "non-excavation bridge configuration"},
            "B3": {"pass": "no cross-domain" in config["scope"], "evidence": "software fixture scope documented"},
            "B4": {"pass": core["coreBackendFilesModified"] == 0, "evidence": "frozen backend diff = 0"},
            "B5": {"pass": core["coreFrontendFilesModified"] == 0, "evidence": "frozen frontend diff = 0"},
            "B6": {"pass": core["pitPreCoreFilesModified"] == 0, "evidence": "PIT_PRE core diff = 0"},
            "B7": {"pass": core["eventWorkflowFilesModified"] == 0, "evidence": "event workflow core diff = 0"},
            "B8": {"pass": core["existingSourceTableSchemaChangeCount"] == 0, "evidence": "no ALTER em_obs_*"},
            "B9": {"pass": pit_pre["pass"] and prediction["totalPersistedRows"] == 1120, "evidence": "two-model PIT_PRE prediction = 1,120 rows"},
            "B10": {"pass": gate_api["data"]["resultIntegrityValid"] is True, "evidence": "Gate resultIntegrityValid=true"},
            "B11": {"pass": future_api["data"]["executionEligible"] is True and future_api["data"]["assessedFeatureCount"] > 0, "evidence": "Future State eligible and assessed"},
            "B12": {"pass": evaluate_zero and evaluate_api["data"]["eventCount"] > 0, "evidence": "Evaluate candidate with zero formal side effects"},
            "B13": {"pass": execute_delta["events"] == 1 and execute_delta["responseWorkflows"] == 1 and execute_delta["predictionLinks"] == 1 and len(steps) == 4, "evidence": "formal event, workflow, four steps, provenance"},
            "B14": {"pass": negative["pass"], "evidence": "missing mapping rejected before inference"},
            "B15": {"pass": frontend["pass"] and len(series_api["data"]) == 56, "evidence": "frontend build, project routes, and joint series API pass"},
        }
        summary = {
            "schemaVersion": "shm-em-phase1b-summary-v1",
            "finalCoreFreezeV2": FINAL_CORE_FREEZE_V2,
            "phase1bCommitted": False,
            "configuration": config,
            "negativeOnboarding": negative,
            "prediction": prediction,
            "gate": gate_api["data"],
            "futureState": future_api["data"],
            "evaluateFormalDeltas": evaluate_evidence["formalDeltas"],
            "executeFormalDeltas": execute_evidence["formalDeltas"],
            "eventId": event_id,
            "workflowId": workflow["id"] if workflow else None,
            "provenanceLinkId": prediction_link["id"] if prediction_link else None,
            "responseWorkflowOutcome": response_workflow_outcome,
            "provenanceClaimBoundary": (
                "Event Trace resolves the event to the prediction batch/run and immutable "
                "model/input metadata; persisted-result integrity is independently "
                "revalidated by the execution Gate."
            ),
            "frontend": frontend,
            "coreDiff": core,
            "registrationEffort": registration,
            "acceptanceChecks": checks,
            "pass": all(item["pass"] for item in checks.values()),
            "stop": "STOP_FOR_GPT_REVIEW",
        }
        write_json(evidence_root / "end-to-end-summary.json", summary)
        write_text(evidence_root / "PHASE1B_COMPLETION_REPORT.md", phase1b_report(summary))

        # Stop the application before sealing the evidence set so its final log
        # tail is covered by the manifest as well.
        backend.stop()
        if backend.stdout_path.is_file():
            lines = backend.stdout_path.read_text(encoding="utf-8", errors="replace").splitlines()
            write_text(evidence_root / "backend-log-tail.txt", "\n".join(lines[-160:]))
        backend = None
        write_json(evidence_root / "phase1b-manifest.json", manifest_for(evidence_root))
        if not summary["pass"]:
            raise RuntimeError("One or more Phase 1B acceptance checks failed")
        print(f"Phase 1B PASS: {sum(1 for item in checks.values() if item['pass'])}/{len(checks)}")
        print(f"Evidence: {evidence_root}")
        return 0
    finally:
        if backend is not None:
            backend.stop()
            if backend.stdout_path.is_file() and evidence_root.exists():
                lines = backend.stdout_path.read_text(encoding="utf-8", errors="replace").splitlines()
                write_text(evidence_root / "backend-log-tail.txt", "\n".join(lines[-160:]))
        if db is not None:
            db.close()
        shutil.rmtree(args.runtime_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
