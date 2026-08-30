#!/usr/bin/env python3
"""Run the Phase 1A SHM-EM failure-path matrix against isolated databases.

This is a revision-only integration harness. It clones one verified public
sample baseline into independent ``shm_em_reproduce_*`` databases, starts the
frozen backend in the ``reproduce`` profile, injects exactly one fault per
case, and records API plus database evidence. It never edits production data.
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
import urllib.request

import pymysql

from persisted_integrity_reference import recompute_batch


CORE_FREEZE_SHA = "df39ffb2b57d16cfdca419adf2492959fcc0931c"
FREEZE_RECORD_SHA = "6ea8ec64ed456fc7ea503e365107c1b3db82737a"
SOURCE_BRANCH = "revision/softx-d-26-00931"
PROJECT_ID = 1
PROJECT_CODE = "SHM_EM_PUBLIC_SAMPLE"

CASE_ORDER = [
    "P00",
    "F01", "F02", "F03", "F04", "F05", "F06",
    "F07", "F08", "F09", "F10", "F11", "F12",
    "I01", "I02",
]

CASE_LABELS = {
    "P00": "Valid reference control",
    "F01": "Incomplete forecast steps",
    "F02": "Stale prediction",
    "F03": "Incorrect model artifact hash",
    "F04": "Missing required target channel",
    "F05": "Invalid engineering unit",
    "F06": "Input-schema mismatch",
    "F07": "Temporal misalignment",
    "F08": "Failed model run",
    "F09": "Corrupted persisted forecast values with stale hashes",
    "F10": "Invalid prediction quality flag",
    "F11": "Batch status failure",
    "F12": "Evaluate then mutate then Execute recheck",
    "I01": "Partial dropped observation",
    "I02": "Entire required feature unavailable",
}

FORMAL_TABLES = {
    "event_delta": "em_monitoring_event",
    "response_workflow_delta": "em_event_response_workflow",
    "response_step_delta": "em_event_response_step",
    "report_delta": "em_report_instance",
    "notification_delta": "em_notification_task",
    "prediction_link_delta": "em_event_prediction_link",
    "evidence_link_delta": "em_event_evidence_link",
    "metric_snapshot_delta": "em_event_metric_snapshot",
    "evidence_resource_delta": "em_evidence_resource",
    "event_state_transition_delta": "em_event_state_transition",
    "event_notification_state_delta": "em_event_notification_state",
    "notification_delivery_delta": "em_notification_delivery_log",
    "handling_log_delta": "em_event_handling_log",
}

AUDIT_TABLES = {
    "audit_gate_delta": "em_prediction_execution_gate",
    "evaluation_run_delta": "em_event_evaluation_run",
    "audit_log_delta": "em_audit_log",
}

MATRIX_FIELDS = [
    "case_id", "reviewer_fault", "fault_injection",
    "expected_rejection_stage", "actual_rejection_stage",
    "model_set_valid", "feature_set_valid", "timeline_valid",
    "quality_valid", "artifact_hash_valid", "freshness_valid",
    "result_integrity_valid",
    "execution_eligible", "gate_issues",
    "evaluate_attempted", "execute_attempted", "execute_rejected",
    *FORMAL_TABLES.keys(), *AUDIT_TABLES.keys(),
    "pass", "finding_code", "notes",
]


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


class Database:
    def __init__(self, args: argparse.Namespace, name: str):
        self.args = args
        self.name = name
        self.connection = pymysql.connect(
            host=args.host,
            port=args.port,
            user=args.app_user,
            password=args.app_password,
            database=name,
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
    def __init__(self, args: argparse.Namespace, database: str, port: int, runtime_root: Path):
        self.args = args
        self.database = database
        self.port = port
        self.runtime_root = runtime_root
        self.process: subprocess.Popen[str] | None = None
        self.stdout_path = runtime_root / "backend.out.log"
        self.stderr_path = runtime_root / "backend.err.log"
        self._stdout = None
        self._stderr = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({
            "DB_URL": (
                f"jdbc:mysql://{self.args.host}:{self.args.port}/{self.database}"
                "?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai"
                "&useSSL=false&allowPublicKeyRetrieval=true"
            ),
            "DB_USERNAME": self.args.app_user,
            "DB_PASSWORD": self.args.app_password,
            "SERVER_PORT": str(self.port),
            "SPRING_PROFILES_ACTIVE": "reproduce",
            "SHM_EM_NOTIFICATION_ENABLED": "false",
            "SHM_EM_NOTIFICATION_TASK_CREATE_ENABLED": "false",
            "SHM_EM_NOTIFICATION_SCHEDULER_ENABLED": "false",
            "SHM_EM_NOTIFICATION_MAIL_SEND_ENABLED": "false",
            "SHM_EM_RESPONSE_AUTOMATION_ENABLED": "false",
            "SHM_EM_REPORT_OUTPUT_DIR": str(self.runtime_root / "reports"),
        })
        self._stdout = self.stdout_path.open("w", encoding="utf-8", newline="\n")
        self._stderr = self.stderr_path.open("w", encoding="utf-8", newline="\n")
        self.process = subprocess.Popen(
            [str(self.args.java), "-jar", str(self.args.backend_jar), "--spring.profiles.active=reproduce"],
            cwd=self.runtime_root,
            env=env,
            stdout=self._stdout,
            stderr=self._stderr,
            text=True,
        )
        deadline = time.time() + self.args.backend_start_timeout
        last_error = "backend did not answer"
        while time.time() < deadline:
            if self.process.poll() is not None:
                last_error = f"backend exited with code {self.process.returncode}"
                break
            response = api_call("GET", self.base_url + "/api/em/projects/1")
            if response["ok"] and response.get("body", {}).get("code") == 0:
                return
            last_error = response.get("error") or str(response.get("body"))
            time.sleep(0.7)
        self.stop()
        out = self.stdout_path.read_text(encoding="utf-8", errors="replace")[-8000:]
        err = self.stderr_path.read_text(encoding="utf-8", errors="replace")[-8000:]
        raise RuntimeError(f"Backend failed to start: {last_error}\nSTDOUT:\n{out}\nSTDERR:\n{err}")

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        if self._stdout:
            self._stdout.close()
        if self._stderr:
            self._stderr.close()


def api_call(method: str, url: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method=method,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else None
            return {"ok": True, "httpStatus": response.status, "body": parsed}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = raw
        return {"ok": False, "httpStatus": exc.code, "body": parsed, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - retained as integration evidence
        return {"ok": False, "httpStatus": None, "body": None, "error": repr(exc)}


def mysql_environment(password: str) -> dict[str, str]:
    env = os.environ.copy()
    env["MYSQL_PWD"] = password
    return env


def mysql_base_args(executable: Path, args: argparse.Namespace, user: str) -> list[str]:
    return [
        str(executable), "--host", args.host, "--port", str(args.port),
        "--user", user, "--default-character-set=utf8mb4",
    ]


def run_checked(command: list[str], *, env: dict[str, str], stdin: Any = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        env=env,
        stdin=stdin,
        cwd=cwd,
        text=stdin is None,
        capture_output=stdin is None,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr if isinstance(result.stderr, str) else ""
        stdout = result.stdout if isinstance(result.stdout, str) else ""
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{stdout}\n{stderr}")
    return result


def create_baseline_dump(args: argparse.Namespace, path: Path) -> None:
    command = mysql_base_args(args.mysqldump, args, args.admin_user) + [
        "--single-transaction", "--routines", "--triggers",
        "--set-gtid-purged=OFF", "--no-tablespaces",
        f"--result-file={path}", args.baseline_database,
    ]
    run_checked(command, env=mysql_environment(args.admin_password))


def clone_database(args: argparse.Namespace, dump_path: Path, database: str) -> None:
    if not re.fullmatch(r"shm_em_reproduce_[A-Za-z0-9_]+", database):
        raise ValueError(f"Unsafe case database name: {database}")
    quoted_password = args.app_password.replace("'", "''")
    sql = (
        f"DROP DATABASE IF EXISTS `{database}`;"
        f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        f"CREATE USER IF NOT EXISTS '{args.app_user}'@'localhost' IDENTIFIED BY '{quoted_password}';"
        f"ALTER USER '{args.app_user}'@'localhost' IDENTIFIED BY '{quoted_password}';"
        f"GRANT ALL PRIVILEGES ON `{database}`.* TO '{args.app_user}'@'localhost';"
        f"CREATE USER IF NOT EXISTS '{args.app_user}'@'%' IDENTIFIED BY '{quoted_password}';"
        f"ALTER USER '{args.app_user}'@'%' IDENTIFIED BY '{quoted_password}';"
        f"GRANT ALL PRIVILEGES ON `{database}`.* TO '{args.app_user}'@'%';"
        "FLUSH PRIVILEGES;"
    )
    command = mysql_base_args(args.mysql, args, args.admin_user) + ["--execute", sql]
    run_checked(command, env=mysql_environment(args.admin_password))
    import_command = mysql_base_args(args.mysql, args, args.admin_user) + [database]
    with dump_path.open("rb") as handle:
        result = subprocess.run(
            import_command,
            env=mysql_environment(args.admin_password),
            stdin=handle,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))


def drop_database(args: argparse.Namespace, database: str) -> None:
    if not re.fullmatch(rf"{re.escape(args.database_prefix)}_[A-Za-z0-9_]+", database):
        raise ValueError(f"Refusing to drop database outside {args.phase_label}: {database}")
    command = mysql_base_args(args.mysql, args, args.admin_user) + [
        "--execute", f"DROP DATABASE IF EXISTS `{database}`;"
    ]
    run_checked(command, env=mysql_environment(args.admin_password))


def count_state(db: Database) -> dict[str, int]:
    result: dict[str, int] = {}
    for key, table in {**FORMAL_TABLES, **AUDIT_TABLES}.items():
        result[key.removesuffix("_delta")] = int(db.scalar(f"SELECT COUNT(*) FROM `{table}`") or 0)
    return result


def delta_state(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    result: dict[str, int] = {}
    for key in [*FORMAL_TABLES.keys(), *AUDIT_TABLES.keys()]:
        base = key.removesuffix("_delta")
        result[key] = int(after.get(base, 0) - before.get(base, 0))
    return result


def formal_is_zero(delta: dict[str, int]) -> bool:
    return all(delta.get(key, 0) == 0 for key in FORMAL_TABLES)


def database_state(db: Database, batch_id: int) -> dict[str, Any]:
    return {
        "database": db.name,
        "capturedAt": dt.datetime.now().isoformat(timespec="seconds"),
        "batch": db.one("SELECT * FROM em_prediction_batch WHERE id=%s", (batch_id,)),
        "runs": db.all(
            "SELECT id, model_id, model_code, model_version, target_type, status, rolling_steps, "
            "artifact_hash, input_schema_hash, result_hash, persisted_result_hash, "
            "persisted_result_hash_version FROM em_prediction_run "
            "WHERE batch_id=%s ORDER BY model_code", (batch_id,)
        ),
        "results": db.one(
            "SELECT COUNT(*) AS rowCount, COUNT(DISTINCT feature_code) AS featureCount, "
            "COUNT(DISTINCT step) AS stepCount, SUM(quality_flag NOT IN ('normal','ok')) AS qualityIssueCount, "
            "SUM(engineering_value IS NULL) AS missingEngineeringCount, "
            "MIN(future_time) AS firstFutureTime, MAX(future_time) AS lastFutureTime "
            "FROM em_prediction_result WHERE batch_id=%s", (batch_id,)
        ),
        "rule": db.one(
            "SELECT * FROM em_event_rule WHERE project_id=%s AND UPPER(input_source)='PREDICTION' "
            "AND enabled=1 ORDER BY id LIMIT 1", (PROJECT_ID,)
        ),
        "counts": count_state(db),
    }


def latest_batch_id(db: Database) -> int:
    value = db.scalar(
        "SELECT id FROM em_prediction_batch WHERE project_id=%s AND status='success' "
        "ORDER BY base_time DESC,id DESC LIMIT 1", (PROJECT_ID,)
    )
    if value is None:
        raise RuntimeError("No successful baseline prediction batch found")
    return int(value)


def prediction_rule(db: Database) -> dict[str, Any]:
    row = db.one(
        "SELECT * FROM em_event_rule WHERE project_id=%s AND UPPER(input_source)='PREDICTION' "
        "AND enabled=1 ORDER BY id LIMIT 1", (PROJECT_ID,)
    )
    if not row:
        raise RuntimeError("No enabled prediction rule found")
    return row


def rule_body(batch_id: int, mode: str) -> dict[str, Any]:
    return {
        "inputSource": "PREDICTION",
        "predictionBatchId": batch_id,
        "predictionExecutionMode": mode,
        "seriesQualityFilter": "normal",
    }


def response_data(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body")
    return body.get("data") if isinstance(body, dict) and isinstance(body.get("data"), dict) else {}


def response_message(response: dict[str, Any]) -> str:
    body = response.get("body")
    if isinstance(body, dict):
        return str(body.get("message") or response.get("error") or "")
    return str(response.get("error") or body or "")


def response_rejected(response: dict[str, Any]) -> bool:
    body = response.get("body")
    return (not response.get("ok")) or (isinstance(body, dict) and body.get("code") != 0)


def gate_columns(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_set_valid": gate.get("modelSetValid"),
        "feature_set_valid": gate.get("featureSetValid"),
        "timeline_valid": gate.get("timelineValid"),
        "quality_valid": gate.get("qualityValid"),
        "artifact_hash_valid": gate.get("artifactHashValid"),
        "freshness_valid": gate.get("freshnessValid"),
        "result_integrity_valid": gate.get("resultIntegrityValid"),
        "execution_eligible": gate.get("executionEligible"),
        "gate_issues": " | ".join(gate.get("issues") or []),
    }


def inject_fault(db: Database, case_id: str, batch_id: int, rule: dict[str, Any]) -> str:
    if case_id in {"P00", "F02", "F12"}:
        return {
            "P00": "-- Positive control: no fault injected.",
            "F02": "-- No data mutation. OPERATIONAL wall-clock freshness is the single fault.",
            "F12": "-- Mutation is applied only after the valid Evaluate call; see api-response.json.",
        }[case_id]

    if case_id == "F01":
        row = db.one(
            "SELECT id,feature_code,step FROM em_prediction_result WHERE batch_id=%s AND step=40 "
            "ORDER BY id LIMIT 1", (batch_id,)
        )
        db.execute("DELETE FROM em_prediction_result WHERE id=%s", (row["id"],))
        return f"DELETE FROM em_prediction_result WHERE id={row['id']}; -- {row['feature_code']} step 40"

    if case_id == "F03":
        row = db.one("SELECT id,artifact_hash FROM em_prediction_run WHERE batch_id=%s ORDER BY id LIMIT 1", (batch_id,))
        bad_hash = "f" * 64 if row["artifact_hash"] != "f" * 64 else "e" * 64
        db.execute("UPDATE em_prediction_run SET artifact_hash=%s WHERE id=%s", (bad_hash, row["id"]))
        return f"UPDATE em_prediction_run SET artifact_hash='{bad_hash}' WHERE id={row['id']};"

    if case_id == "F04":
        row = db.one(
            "SELECT p.feature_code,COUNT(*) AS row_count FROM em_prediction_result p "
            "JOIN em_prediction_feature_mapping f ON f.project_id=p.project_id "
            "AND f.model_id=p.model_id AND f.feature_code=p.feature_code "
            "WHERE p.batch_id=%s AND f.prediction_target=1 AND f.required=1 "
            "AND p.feature_code<>%s GROUP BY p.feature_code ORDER BY p.feature_code LIMIT 1",
            (batch_id, rule["prediction_feature_code"]),
        )
        db.execute("DELETE FROM em_prediction_result WHERE batch_id=%s AND feature_code=%s", (batch_id, row["feature_code"]))
        return (
            "DELETE FROM em_prediction_result "
            f"WHERE batch_id={batch_id} AND feature_code='{row['feature_code']}'; -- {row['row_count']} rows"
        )

    if case_id == "F05":
        feature = rule["prediction_feature_code"]
        db.execute(
            "UPDATE em_prediction_result SET engineering_unit='kPa' WHERE batch_id=%s AND feature_code=%s",
            (batch_id, feature),
        )
        recompute_batch(db, batch_id)
        return (
            "UPDATE em_prediction_result SET engineering_unit='kPa' "
            f"WHERE batch_id={batch_id} AND feature_code='{feature}';\n"
            "-- persisted result/output integrity hashes recomputed by the independent Phase 1A.1 helper"
        )

    if case_id == "F06":
        row = db.one("SELECT id,input_schema_hash FROM em_prediction_run WHERE batch_id=%s ORDER BY id LIMIT 1", (batch_id,))
        bad_hash = "a" * 64 if row["input_schema_hash"] != "a" * 64 else "b" * 64
        db.execute("UPDATE em_prediction_run SET input_schema_hash=%s WHERE id=%s", (bad_hash, row["id"]))
        return f"UPDATE em_prediction_run SET input_schema_hash='{bad_hash}' WHERE id={row['id']};"

    if case_id == "F07":
        row = db.one("SELECT id,future_time FROM em_prediction_result WHERE batch_id=%s ORDER BY id LIMIT 1", (batch_id,))
        db.execute("UPDATE em_prediction_result SET future_time=DATE_ADD(future_time,INTERVAL 10 SECOND) WHERE id=%s", (row["id"],))
        return f"UPDATE em_prediction_result SET future_time=DATE_ADD(future_time, INTERVAL 10 SECOND) WHERE id={row['id']};"

    if case_id == "F08":
        row = db.one("SELECT id,model_code FROM em_prediction_run WHERE batch_id=%s ORDER BY id LIMIT 1", (batch_id,))
        db.execute("UPDATE em_prediction_run SET status='failed' WHERE id=%s", (row["id"],))
        return f"UPDATE em_prediction_run SET status='failed' WHERE id={row['id']}; -- {row['model_code']}"

    if case_id == "F09":
        feature = rule["prediction_feature_code"]
        threshold = decimal.Decimal(rule["threshold_value"])
        corrupt_value = threshold + decimal.Decimal("100")
        db.execute(
            "UPDATE em_prediction_result SET predicted_value=%s,engineering_value=%s "
            "WHERE batch_id=%s AND feature_code=%s",
            (corrupt_value, corrupt_value, batch_id, feature),
        )
        return (
            "-- Intentionally leave em_prediction_run.result_hash and em_prediction_batch.output_hash unchanged.\n"
            f"UPDATE em_prediction_result SET predicted_value={corrupt_value}, engineering_value={corrupt_value} "
            f"WHERE batch_id={batch_id} AND feature_code='{feature}';"
        )

    if case_id == "F10":
        row = db.one("SELECT id,feature_code,step FROM em_prediction_result WHERE batch_id=%s ORDER BY id LIMIT 1", (batch_id,))
        db.execute("UPDATE em_prediction_result SET quality_flag='review' WHERE id=%s", (row["id"],))
        return f"UPDATE em_prediction_result SET quality_flag='review' WHERE id={row['id']}; -- {row['feature_code']} step {row['step']}"

    if case_id == "F11":
        db.execute("UPDATE em_prediction_batch SET status='failed' WHERE id=%s", (batch_id,))
        return f"UPDATE em_prediction_batch SET status='failed' WHERE id={batch_id};"

    raise ValueError(f"Unsupported fault case {case_id}")


def expected_stage(case_id: str) -> str:
    if case_id in {"F01", "F02", "F03", "F04", "F06", "F07", "F08", "F10", "F11"}:
        return "EXECUTION_GATE"
    if case_id == "F05":
        return "RULE_VALIDATION"
    if case_id == "F09":
        return "PERSISTED_RESULT_INTEGRITY"
    if case_id == "F12":
        return "EXECUTE_RECHECK"
    if case_id == "I01":
        return "INPUT_ALIGNMENT_POLICY"
    if case_id == "I02":
        return "INPUT_ASSEMBLY"
    return "POSITIVE_CONTROL"


def evaluate_case_result(case_id: str, row: dict[str, Any], gate: dict[str, Any], execute: dict[str, Any],
                         evaluate: dict[str, Any] | None, evaluate_delta: dict[str, int] | None) -> None:
    rejected = response_rejected(execute) if row["execute_attempted"] else False
    row["execute_rejected"] = rejected
    formal_zero = formal_is_zero(row)
    eligible = gate.get("executionEligible")
    issue_text = " | ".join(gate.get("issues") or [])

    expected_false_field = {
        "F01": "timelineValid",
        "F02": "freshnessValid",
        "F03": "artifactHashValid",
        "F04": "featureSetValid",
        "F06": "artifactHashValid",
        "F07": "timelineValid",
        "F08": "modelSetValid",
        "F10": "qualityValid",
    }.get(case_id)

    if case_id == "P00":
        eval_data = response_data(evaluate or {})
        execute_data = response_data(execute)
        all_gate_valid = all(gate.get(key) is True for key in (
            "modelSetValid", "featureSetValid", "timelineValid", "qualityValid",
            "artifactHashValid", "freshnessValid", "resultIntegrityValid", "executionEligible",
        ))
        eval_formal_zero = evaluate_delta is not None and formal_is_zero(evaluate_delta)
        execute_ok = not rejected and bool(execute_data.get("event"))
        provenance_ok = row["prediction_link_delta"] >= 1 and row["response_workflow_delta"] >= 1
        row["actual_rejection_stage"] = "NONE"
        row["pass"] = all_gate_valid and eval_data.get("eventCount", 0) >= 1 and eval_formal_zero and execute_ok and provenance_ok
        row["finding_code"] = "" if row["pass"] else "POSITIVE_CONTROL_FAILED"
        row["notes"] = f"Evaluate formal side effects zero={eval_formal_zero}; Execute provenance complete={provenance_ok}"
        return

    if case_id == "F05":
        unit_rejected = rejected and "unit" in response_message(execute).lower()
        row["actual_rejection_stage"] = "RULE_VALIDATION" if eligible and unit_rejected else ("EXECUTION_GATE" if not eligible else "NONE")
        row["pass"] = eligible is True and unit_rejected and formal_zero
        row["finding_code"] = "" if row["pass"] else "UNIT_VALIDATION_PATH_FAILED"
        row["notes"] = response_message(execute)
        return

    if case_id == "F09":
        blocked = gate.get("resultIntegrityValid") is False and eligible is False and rejected and formal_zero
        row["actual_rejection_stage"] = "PERSISTED_RESULT_INTEGRITY" if blocked else "NONE"
        row["pass"] = blocked
        row["finding_code"] = "" if blocked else "PERSISTED_RESULT_INTEGRITY_GAP"
        row["notes"] = (
            f"resultIntegrityValid={gate.get('resultIntegrityValid')}; Gate eligible={eligible}; "
            f"Execute rejected={rejected}; formal event delta={row['event_delta']}; "
            "persisted integrity hashes intentionally unchanged"
        )
        return

    if case_id == "F11":
        row["actual_rejection_stage"] = "EXECUTION_GATE" if not eligible and rejected else "NONE"
        row["pass"] = eligible is False and rejected and formal_zero and "Batch status is not success" in issue_text
        row["finding_code"] = "" if row["pass"] else "BATCH_STATUS_GATE_FAILED"
        row["notes"] = response_message(execute)
        return

    if case_id == "F12":
        eval_data = response_data(evaluate or {})
        eval_formal_zero = evaluate_delta is not None and formal_is_zero(evaluate_delta)
        row["actual_rejection_stage"] = "EXECUTE_RECHECK" if rejected and gate.get("resultIntegrityValid") is False else "NONE"
        row["pass"] = (
            eval_data.get("eventCount", 0) >= 1
            and eval_data.get("executionEligible") is True
            and eval_formal_zero
            and gate.get("resultIntegrityValid") is False
            and eligible is False
            and rejected
            and formal_zero
        )
        row["finding_code"] = "" if row["pass"] else "EXECUTE_RECHECK_NOT_EFFECTIVE"
        row["notes"] = f"Evaluate side-effect-free={eval_formal_zero}; Execute response={response_message(execute)}"
        return

    expected_invalid = expected_false_field is not None and gate.get(expected_false_field) is False
    row["actual_rejection_stage"] = "EXECUTION_GATE" if eligible is False and rejected else "NONE"
    row["pass"] = expected_invalid and eligible is False and rejected and formal_zero
    row["finding_code"] = "" if row["pass"] else f"{case_id}_EXPECTED_GATE_REJECTION_FAILED"
    row["notes"] = response_message(execute)


def run_api_case(args: argparse.Namespace, dump_path: Path, case_id: str, case_index: int) -> dict[str, Any]:
    database = f"{args.database_prefix}_{case_id.lower()}"
    case_dir = args.evidence_root / "cases" / case_id
    clone_database(args, dump_path, database)
    db = Database(args, database)
    backend: Backend | None = None
    try:
        batch_id = latest_batch_id(db)
        rule = prediction_rule(db)
        before_state = database_state(db, batch_id)
        before_counts = before_state["counts"]
        write_json(case_dir / "state-before.json", before_state)
        mutation_sql = inject_fault(db, case_id, batch_id, rule)
        write_text(case_dir / "mutation.sql", mutation_sql)

        runtime_root = args.runtime_root / case_id
        backend = Backend(args, database, args.backend_port, runtime_root)
        backend.start()

        gate_response: dict[str, Any]
        evaluate_response: dict[str, Any] | None = None
        execute_response: dict[str, Any]
        evaluate_delta: dict[str, int] | None = None

        if case_id == "P00":
            gate_response = api_call(
                "POST",
                backend.base_url + f"/api/em/predictions/batches/{batch_id}/execution-gate/evaluate?mode=REPRODUCTION",
            )
            pre_evaluate_counts = count_state(db)
            evaluate_response = api_call(
                "POST",
                backend.base_url + f"/api/em/projects/{PROJECT_ID}/rules/{rule['id']}/evaluate",
                rule_body(batch_id, "REPLAY"),
            )
            post_evaluate_counts = count_state(db)
            evaluate_delta = delta_state(pre_evaluate_counts, post_evaluate_counts)
            execute_response = api_call(
                "POST",
                backend.base_url + f"/api/em/projects/{PROJECT_ID}/rules/{rule['id']}/execute",
                rule_body(batch_id, "REPRODUCTION"),
            )
        elif case_id == "F12":
            pre_evaluate_counts = count_state(db)
            evaluate_response = api_call(
                "POST",
                backend.base_url + f"/api/em/projects/{PROJECT_ID}/rules/{rule['id']}/evaluate",
                rule_body(batch_id, "REPLAY"),
            )
            post_evaluate_counts = count_state(db)
            evaluate_delta = delta_state(pre_evaluate_counts, post_evaluate_counts)
            result = db.one("SELECT id,engineering_value FROM em_prediction_result WHERE batch_id=%s ORDER BY id LIMIT 1", (batch_id,))
            changed_value = decimal.Decimal(result["engineering_value"] or 0) + decimal.Decimal("1")
            db.execute("UPDATE em_prediction_result SET engineering_value=%s WHERE id=%s", (changed_value, result["id"]))
            mutation_sql = (
                "-- Applied after valid Evaluate and before Execute.\n"
                f"UPDATE em_prediction_result SET engineering_value={changed_value} WHERE id={result['id']};\n"
                "-- persisted integrity hashes intentionally remain unchanged"
            )
            write_text(
                case_dir / "mutation.sql",
                mutation_sql,
            )
            execute_response = api_call(
                "POST",
                backend.base_url + f"/api/em/projects/{PROJECT_ID}/rules/{rule['id']}/execute",
                rule_body(batch_id, "REPRODUCTION"),
            )
            gate_response = api_call(
                "GET",
                backend.base_url + f"/api/em/predictions/batches/{batch_id}/execution-gate?mode=REPRODUCTION",
            )
        else:
            mode = "OPERATIONAL" if case_id == "F02" else "REPRODUCTION"
            gate_response = api_call(
                "POST",
                backend.base_url + f"/api/em/predictions/batches/{batch_id}/execution-gate/evaluate?mode={mode}",
            )
            execute_response = api_call(
                "POST",
                backend.base_url + f"/api/em/projects/{PROJECT_ID}/rules/{rule['id']}/execute",
                rule_body(batch_id, mode),
            )

        after_state = database_state(db, batch_id)
        write_json(case_dir / "state-after.json", after_state)
        gate = response_data(gate_response)
        write_json(case_dir / "gate.json", gate_response)
        write_json(case_dir / "api-response.json", {
            "gate": gate_response,
            "evaluate": evaluate_response,
            "evaluateFormalSideEffectDelta": evaluate_delta,
            "execute": execute_response,
        })

        row: dict[str, Any] = {
            "case_id": case_id,
            "reviewer_fault": CASE_LABELS[case_id],
            "fault_injection": mutation_sql.replace("\n", " "),
            "expected_rejection_stage": expected_stage(case_id),
            "actual_rejection_stage": "",
            **gate_columns(gate),
            "evaluate_attempted": evaluate_response is not None,
            "execute_attempted": True,
            "execute_rejected": response_rejected(execute_response),
            **delta_state(before_counts, after_state["counts"]),
            "pass": False,
            "finding_code": "",
            "notes": "",
        }
        evaluate_case_result(case_id, row, gate, execute_response, evaluate_response, evaluate_delta)
        write_json(case_dir / "case-summary.json", row)
        return row
    finally:
        if backend:
            backend.stop()
        db.close()
        if args.drop_case_databases:
            drop_database(args, database)


def required_input_feature(db: Database) -> dict[str, Any]:
    row = db.one(
        "SELECT f.id,f.model_id,m.model_code,f.feature_code,f.source_registry_code,"
        "f.source_metric_code,f.station_id,f.instrument_id,r.physical_table_name "
        "FROM em_prediction_feature_mapping f "
        "JOIN em_prediction_model m ON m.id=f.model_id "
        "JOIN em_observation_table_registry r ON r.registry_code=f.source_registry_code "
        "WHERE f.project_id=%s AND f.required=1 AND f.feature_role='model_input' "
        "AND m.model_code='Pressure' ORDER BY f.feature_order LIMIT 1",
        (PROJECT_ID,),
    )
    if not row or not re.fullmatch(r"em_[A-Za-z0-9_]+", row["physical_table_name"]):
        raise RuntimeError("Unable to resolve a safe required input feature")
    return row


def alignment_summary(db: Database, batch_id: int, model_code: str) -> dict[str, Any]:
    row = db.one(
        "SELECT input_snapshot_json FROM em_prediction_run WHERE batch_id=%s AND model_code=%s ORDER BY id DESC LIMIT 1",
        (batch_id, model_code),
    )
    if not row:
        return {}
    value = row["input_snapshot_json"]
    if isinstance(value, str):
        return json.loads(value)
    return value or {}


def fill_count(snapshot: dict[str, Any]) -> int:
    quality = snapshot.get("qualitySummary") or {}
    fields = (
        "interiorInterpolationCellCount", "leadingBoundaryExtensionCellCount",
        "trailingBoundaryExtensionCellCount", "forwardFillCellCount", "backwardFillCellCount",
    )
    return sum(int(quality.get(field) or 0) for field in fields)


def run_pit_pre(args: argparse.Namespace, database: str) -> dict[str, Any]:
    config = {
        "database": {
            "host": args.host,
            "port": args.port,
            "user": args.app_user,
            "password": args.app_password,
            "database": database,
            "charset": "utf8mb4",
        },
        "working_directory": str(args.pit_pre_root),
    }
    config_path = args.runtime_root / f"pit-pre-{database}.json"
    write_json(config_path, config)
    try:
        result = subprocess.run(
            [str(args.python), "-m", "pit_pre", "--config", str(config_path), "--project-code", PROJECT_CODE],
            cwd=args.pit_pre_root,
            text=True,
            capture_output=True,
            timeout=args.pit_pre_timeout,
            check=False,
        )
        return {"exitCode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    finally:
        config_path.unlink(missing_ok=True)


def run_input_case(args: argparse.Namespace, dump_path: Path, case_id: str) -> dict[str, Any]:
    database = f"{args.database_prefix}_{case_id.lower()}"
    case_dir = args.evidence_root / "cases" / case_id
    clone_database(args, dump_path, database)
    db = Database(args, database)
    try:
        batch_id = latest_batch_id(db)
        feature = required_input_feature(db)
        before_state = database_state(db, batch_id)
        before_counts = before_state["counts"]
        before_snapshot = alignment_summary(db, batch_id, feature["model_code"])
        before_batch_count = int(db.scalar("SELECT COUNT(*) FROM em_prediction_batch") or 0)
        before_max_batch = int(db.scalar("SELECT COALESCE(MAX(id),0) FROM em_prediction_batch") or 0)
        write_json(case_dir / "state-before.json", {
            **before_state,
            "selectedFeature": feature,
            "baselineAlignmentSnapshot": before_snapshot,
        })

        table = feature["physical_table_name"]
        rows = db.all(
            f"SELECT id,observed_at FROM `{table}` WHERE instrument_id=%s AND metric_code=%s ORDER BY observed_at,id",
            (feature["instrument_id"], feature["source_metric_code"]),
        )
        if not rows:
            raise RuntimeError(f"No observation history found for {case_id}")
        if case_id == "I01":
            victim = rows[len(rows) // 2]
            db.execute(f"DELETE FROM `{table}` WHERE id=%s", (victim["id"],))
            mutation_sql = f"DELETE FROM `{table}` WHERE id={victim['id']}; -- one interior sample at {victim['observed_at']}"
        else:
            db.execute(
                f"DELETE FROM `{table}` WHERE instrument_id=%s AND metric_code=%s",
                (feature["instrument_id"], feature["source_metric_code"]),
            )
            mutation_sql = (
                f"DELETE FROM `{table}` WHERE instrument_id={feature['instrument_id']} "
                f"AND metric_code='{feature['source_metric_code']}'; -- entire required feature history"
            )
        write_text(case_dir / "mutation.sql", mutation_sql)

        pit_response = run_pit_pre(args, database)
        after_batch_count = int(db.scalar("SELECT COUNT(*) FROM em_prediction_batch") or 0)
        new_batches = db.all(
            "SELECT id,batch_code,status,model_count,feature_count,rolling_steps,message FROM em_prediction_batch "
            "WHERE id>%s ORDER BY id", (before_max_batch,)
        )
        successful_new = [row for row in new_batches if str(row["status"]).lower() == "success"]
        latest_new_id = int(new_batches[-1]["id"]) if new_batches else None
        latest_snapshot = alignment_summary(db, latest_new_id, feature["model_code"]) if latest_new_id else {}
        new_result_count = int(db.scalar(
            "SELECT COUNT(*) FROM em_prediction_result WHERE batch_id>%s", (before_max_batch,)
        ) or 0)
        new_run_count = int(db.scalar(
            "SELECT COUNT(*) FROM em_prediction_run WHERE batch_id>%s", (before_max_batch,)
        ) or 0)
        after_state = database_state(db, batch_id)
        after_state.update({
            "newBatches": new_batches,
            "newRunCount": new_run_count,
            "newResultCount": new_result_count,
            "latestNewAlignmentSnapshot": latest_snapshot,
        })
        write_json(case_dir / "state-after.json", after_state)
        write_json(case_dir / "gate.json", {"notApplicable": True, "reason": "PIT_PRE input-assembly integration case"})
        write_json(case_dir / "api-response.json", {"pitPre": pit_response})

        deltas = delta_state(before_counts, after_state["counts"])
        baseline_fill = fill_count(before_snapshot)
        new_fill = fill_count(latest_snapshot)
        unresolved = int((latest_snapshot.get("qualitySummary") or {}).get("unresolvedMissingCellCount") or 0)
        if case_id == "I01":
            passed = (
                pit_response["exitCode"] == 0
                and len(successful_new) == 1
                and unresolved == 0
                and new_fill > baseline_fill
                and new_result_count == 4960
            )
            finding = "" if passed else "PARTIAL_DROP_ALIGNMENT_AUDIT_FAILED"
            notes = (
                f"baseline fill cells={baseline_fill}; new fill cells={new_fill}; "
                f"unresolved missing={unresolved}; new results={new_result_count}"
            )
            actual_stage = "INPUT_ALIGNMENT_POLICY" if pit_response["exitCode"] == 0 else "INPUT_ASSEMBLY_REJECTION"
        else:
            passed = (
                pit_response["exitCode"] != 0
                and len(successful_new) == 0
                and new_result_count == 0
            )
            finding = "" if passed else "MISSING_REQUIRED_FEATURE_NOT_REJECTED"
            notes = (
                f"PIT_PRE exit={pit_response['exitCode']}; successful new batches={len(successful_new)}; "
                f"new runs={new_run_count}; new results={new_result_count}"
            )
            actual_stage = "INPUT_ASSEMBLY" if pit_response["exitCode"] != 0 else "NONE"

        row: dict[str, Any] = {
            "case_id": case_id,
            "reviewer_fault": CASE_LABELS[case_id],
            "fault_injection": mutation_sql,
            "expected_rejection_stage": expected_stage(case_id),
            "actual_rejection_stage": actual_stage,
            "model_set_valid": None,
            "feature_set_valid": None,
            "timeline_valid": None,
            "quality_valid": None,
            "artifact_hash_valid": None,
            "freshness_valid": None,
            "result_integrity_valid": None,
            "execution_eligible": None,
            "gate_issues": "",
            "evaluate_attempted": False,
            "execute_attempted": False,
            "execute_rejected": False,
            **deltas,
            "pass": passed,
            "finding_code": finding,
            "notes": notes,
        }
        write_json(case_dir / "case-summary.json", row)
        return row
    finally:
        db.close()
        if args.drop_case_databases:
            drop_database(args, database)


def write_matrices(args: argparse.Namespace, rows: list[dict[str, Any]]) -> None:
    matrix_stem = "failure-matrix-v2" if args.phase_label == "phase1a1" else "failure-matrix"
    write_json(args.evidence_root / f"{matrix_stem}.json", rows)
    with (args.evidence_root / f"{matrix_stem}.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MATRIX_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value for key, value in row.items()})

    lines = [
        f"# {args.phase_label_display} Failure-Path Matrix",
        "",
        f"- Core freeze: `{CORE_FREEZE_SHA}`",
        f"- Freeze record: `{FREEZE_RECORD_SHA}`",
        f"- Database policy: independent `{args.database_prefix}_*` database per case",
        "- Production changes: restricted to the authorized persisted-integrity repair",
        "",
        "| Case | Fault | Expected stage | Actual stage | Eligible | Formal event delta | Result | Finding |",
        "|---|---|---|---|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['reviewer_fault']} | {row['expected_rejection_stage']} | "
            f"{row['actual_rejection_stage']} | {row['execution_eligible']} | {row['event_delta']} | "
            f"{'PASS' if row['pass'] else 'FAIL'} | {row['finding_code'] or '-'} |"
        )
    lines.extend(["", "## Interpretation", ""])
    if args.phase_label == "phase1a1":
        lines.append(
            "Phase 1A.1 reruns the same isolated failure-path matrix against the authorized "
            "persisted-integrity repair. The original Phase 1A discovery evidence remains preserved separately."
        )
    else:
        lines.append("A failed discovery case is retained as an empirical finding. This Phase 1A harness does not repair production code.")
    write_text(args.evidence_root / f"{matrix_stem}.md", "\n".join(lines))


def write_manifest(args: argparse.Namespace, rows: list[dict[str, Any]], test_results: dict[str, Any]) -> None:
    artifacts = []
    for path in sorted(args.evidence_root.rglob("*")):
        if path.is_file() and path.name != args.manifest_name:
            artifacts.append({
                "path": path.relative_to(args.repo_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    failed = [row for row in rows if not row["pass"]]
    discovery = [row for row in rows if row.get("finding_code") == "PERSISTED_RESULT_INTEGRITY_GAP"]
    manifest = {
        "schemaVersion": "shm-em-phase1a1-manifest-v1" if args.phase_label == "phase1a1" else "shm-em-phase1a-manifest-v1",
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "coreFreezeCommit": CORE_FREEZE_SHA,
        "freezeRecordCommit": FREEZE_RECORD_SHA,
        "sourceBranch": SOURCE_BRANCH,
        "positiveControlPassed": bool(rows and rows[0]["case_id"] == "P00" and rows[0]["pass"]),
        "caseCount": len(rows),
        "passedCount": len(rows) - len(failed),
        "failedCount": len(failed),
        "discoveryGapCount": len(discovery),
        "formalSideEffectTables": list(FORMAL_TABLES.values()),
        "auditTables": list(AUDIT_TABLES.values()),
        "isolatedDatabasePattern": f"^{args.database_prefix}_[A-Za-z0-9_]+$",
        "baselineDatabase": args.baseline_database,
        "backendTests": test_results.get("backend"),
        "pitPreTests": test_results.get("pitPre"),
        "artifacts": artifacts,
    }
    write_json(args.evidence_root / args.manifest_name, manifest)


def run_test_command(command: list[str], cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.time()
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
    return {
        "command": command,
        "exitCode": result.returncode,
        "elapsedSeconds": round(time.time() - started, 3),
        "stdoutTail": result.stdout[-12000:],
        "stderrTail": result.stderr[-12000:],
        "passed": result.returncode == 0,
    }


def run_regression_tests(args: argparse.Namespace) -> dict[str, Any]:
    backend = run_test_command([str(args.maven), "-q", "test"], args.backend_root, 300)
    pit_pre = run_test_command(
        [str(args.python), "-m", "unittest", "discover", "-s", "tests", "-v"],
        args.pit_pre_root,
        300,
    )
    result = {"backend": backend, "pitPre": pit_pre}
    write_json(args.evidence_root / "regression-tests.json", result)
    return result


def git_evidence(args: argparse.Namespace) -> dict[str, Any]:
    def git(*parts: str) -> str:
        result = subprocess.run(["git", *parts], cwd=args.repo_root, text=True, capture_output=True, check=True)
        return result.stdout.rstrip()

    frozen_paths = ["src/backend/src/main", "src/frontend", "src/pit_pre/pit_pre", ".gitattributes"]
    frozen_diff = git("diff", "--name-only", "--", *frozen_paths)
    evidence = {
        "head": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "coreFreezeCommit": CORE_FREEZE_SHA,
        "freezeRecordCommit": FREEZE_RECORD_SHA,
        "frozenPaths": frozen_paths,
        "frozenProductionCoreDiff": frozen_diff.splitlines() if frozen_diff else [],
        "gitDiffNameOnly": git("diff", "--name-only").splitlines(),
        "gitStatusShort": git("status", "--short").splitlines(),
    }
    write_json(args.evidence_root / "production-core-diff.json", evidence)
    return evidence


def resolve_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Run SHM-EM Phase 1A failure-path validation")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--admin-user", default="root")
    parser.add_argument("--admin-password", default=os.environ.get("DB_ADMIN_PASSWORD"))
    parser.add_argument("--app-user", default="shm_em_reproduce")
    parser.add_argument("--app-password", default=os.environ.get("MYSQL_PASSWORD"))
    parser.add_argument("--phase-label", choices=["phase1a", "phase1a1"], default="phase1a1")
    parser.add_argument("--baseline-database")
    parser.add_argument("--backend-port", type=int, default=5192)
    parser.add_argument("--backend-start-timeout", type=int, default=90)
    parser.add_argument("--pit-pre-timeout", type=int, default=300)
    parser.add_argument("--drop-case-databases", action="store_true")
    parser.add_argument("--skip-regression-tests", action="store_true")
    parser.add_argument("--finalize-only", action="store_true")
    parser.add_argument("--cases", nargs="+", choices=CASE_ORDER, default=CASE_ORDER)
    parser.add_argument("--mysql", type=Path, default=Path(r"D:\Tools\mysql-8.0.41\bin\mysql.exe"))
    parser.add_argument("--mysqldump", type=Path, default=Path(r"D:\Tools\mysql-8.0.41\bin\mysqldump.exe"))
    parser.add_argument("--python", type=Path, default=Path(r"D:\anaconda3\envs\py310\python.exe"))
    parser.add_argument("--java", type=Path, default=Path(r"C:\Users\nlfdz\.jdks\temurin-1.8.0_482\bin\java.exe"))
    parser.add_argument("--maven", type=Path, default=Path(r"D:\Tools\apache-maven-3.9.16\bin\mvn.cmd"))
    args = parser.parse_args()
    if not args.admin_password or not args.app_password:
        parser.error("Set DB_ADMIN_PASSWORD and MYSQL_PASSWORD (passwords are never written to evidence).")

    args.repo_root = repo_root
    args.phase_label_display = "Phase 1A.1" if args.phase_label == "phase1a1" else "Phase 1A"
    args.database_prefix = "shm_em_reproduce_phase1a1" if args.phase_label == "phase1a1" else "shm_em_reproduce_phase1a"
    args.baseline_database = args.baseline_database or f"{args.database_prefix}_base"
    args.manifest_name = "phase1a1-manifest-v2.json" if args.phase_label == "phase1a1" else "phase1a-manifest.json"
    args.backend_root = repo_root / "src" / "backend"
    args.pit_pre_root = repo_root / "src" / "pit_pre"
    args.evidence_root = (repo_root / "artifacts" / "revision" / "phase1a_1" / "failure-path-v2"
                          if args.phase_label == "phase1a1"
                          else repo_root / "artifacts" / "revision" / "failure-path")
    args.runtime_root = Path(tempfile.mkdtemp(prefix=f"shm-em-{args.phase_label}-"))
    jars = sorted(
        (args.backend_root / "target").glob("*.jar"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    args.backend_jar = next((item for item in jars if not item.name.endswith(".original")), None)
    if not args.backend_jar:
        parser.error("Backend jar is missing. Run Maven package without modifying source code.")
    for executable in (args.mysql, args.mysqldump, args.python, args.java, args.maven):
        if not executable.is_file():
            parser.error(f"Executable not found: {executable}")
    return args


def main() -> int:
    args = resolve_args()
    args.evidence_root.mkdir(parents=True, exist_ok=True)
    dump_path = args.runtime_root / "failure-base.sql"
    rows: list[dict[str, Any]] = []
    try:
        if args.finalize_only:
            matrix_name = "failure-matrix-v2.json" if args.phase_label == "phase1a1" else "failure-matrix.json"
            rows = json.loads((args.evidence_root / matrix_name).read_text(encoding="utf-8"))
            tests = json.loads((args.evidence_root / "regression-tests.json").read_text(encoding="utf-8"))
            git_evidence(args)
            write_manifest(args, rows, tests)
            print(json.dumps({"finalized": True, "evidenceRoot": str(args.evidence_root)}, indent=2))
            return 0
        create_baseline_dump(args, dump_path)
        for index, case_id in enumerate(args.cases):
            print(f"[{index + 1}/{len(args.cases)}] {case_id} - {CASE_LABELS[case_id]}", flush=True)
            if case_id.startswith("I"):
                row = run_input_case(args, dump_path, case_id)
            else:
                row = run_api_case(args, dump_path, case_id, index)
            rows.append(row)
            write_matrices(args, rows)
            print(f"  -> {'PASS' if row['pass'] else 'FAIL'} {row['finding_code']}", flush=True)

        tests = {"backend": {"skipped": True}, "pitPre": {"skipped": True}}
        if not args.skip_regression_tests:
            tests = run_regression_tests(args)
        git_state = git_evidence(args)
        write_manifest(args, rows, tests)
        print(json.dumps({
            "cases": len(rows),
            "passed": sum(1 for row in rows if row["pass"]),
            "failed": sum(1 for row in rows if not row["pass"]),
            "frozenProductionCoreDiff": git_state["frozenProductionCoreDiff"],
            "evidenceRoot": str(args.evidence_root),
        }, indent=2))
        return 0
    finally:
        shutil.rmtree(args.runtime_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
