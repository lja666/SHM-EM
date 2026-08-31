#!/usr/bin/env python3
"""Shared, benchmark-only support for the Phase 2A evidence harness."""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import tempfile
import time
from typing import Any, Iterable
import urllib.error
import urllib.parse
import urllib.request

import pymysql


FINAL_CORE_FREEZE_V2 = "b41c1894f75561c8ef682062a5e6dab35c3916a7"
PHASE1B_COMMIT = "2107674"
FROZEN_PATHS = (
    "src/backend/src/main",
    "src/frontend/src",
    "src/pit_pre/pit_pre",
    ".gitattributes",
)
SCHEMA_SCRIPTS = (
    "00_SHM_EM_complete_schema.sql",
    "01_SHM_EM_conversion_operators.sql",
    "02_SHM_EM_public_sample.sql",
    "03_SHM_EM_public_validation.sql",
    "04_SHM_EM_persisted_prediction_integrity.sql",
)


def utc_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def json_default(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    try:
        from decimal import Decimal

        if isinstance(value, Decimal):
            return str(value)
    except ImportError:
        pass
    raise TypeError(f"Cannot serialize {type(value).__name__}")


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
    elapsed = time.perf_counter() - started
    output = completed.stdout or ""
    return {
        "command": command,
        "exitCode": completed.returncode,
        "elapsedSeconds": round(elapsed, 6),
        "outputTail": output.splitlines()[-160:],
        "pass": completed.returncode == 0,
    }


def command_version(command: list[str], cwd: Path) -> dict[str, Any]:
    try:
        result = run_command(command, cwd, 30)
        return {
            "available": result["pass"],
            "command": command,
            "output": "\n".join(result["outputTail"][:8]).strip() or "unknown",
        }
    except Exception as exc:
        return {"available": False, "command": command, "output": "unknown", "error": str(exc)}


def summary(values_ms: list[float]) -> dict[str, Any]:
    if not values_ms:
        return {"count": 0, "medianMs": None, "p95Ms": None, "minMs": None, "maxMs": None, "meanMs": None, "stddevMs": None}
    ordered = sorted(float(item) for item in values_ms)
    p95_index = max(0, min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1))
    return {
        "count": len(ordered),
        "medianMs": round(statistics.median(ordered), 6),
        "p95Ms": round(ordered[p95_index], 6),
        "minMs": round(ordered[0], 6),
        "maxMs": round(ordered[-1], 6),
        "meanMs": round(statistics.mean(ordered), 6),
        "stddevMs": round(statistics.pstdev(ordered), 6),
        "outliersRemoved": 0,
    }


class Database:
    def __init__(self, args, database: str | None = None):
        self.args = args
        self.database = database or args.database
        self.connection = pymysql.connect(
            host=args.db_host,
            port=args.db_port,
            user=args.db_user,
            password=args.db_password,
            database=self.database,
            charset="utf8mb4",
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def close(self) -> None:
        self.connection.close()

    def scalar(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        row = self.one(sql, params)
        return None if row is None else next(iter(row.values()))

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

    def insert(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return int(cursor.lastrowid)

    def executemany(self, sql: str, rows: list[tuple[Any, ...]]) -> int:
        with self.connection.cursor() as cursor:
            return cursor.executemany(sql, rows)


def mysql_command(args, database: str | None = None) -> list[str]:
    command = [
        str(args.mysql),
        "--protocol=tcp",
        f"--host={args.db_host}",
        f"--port={args.db_port}",
        f"--user={args.db_user}",
        "--default-character-set=utf8mb4",
    ]
    if database:
        command.append(database)
    return command


def mysql_env(args) -> dict[str, str]:
    env = os.environ.copy()
    env["MYSQL_PWD"] = args.db_password
    return env


def initialize_database(args, database: str) -> list[dict[str, Any]]:
    if not database.startswith("shm_em_reproduce_benchmark_"):
        raise ValueError("Benchmark database must match shm_em_reproduce_benchmark_*")
    admin_sql = f"DROP DATABASE IF EXISTS `{database}`; CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    created = subprocess.run(
        mysql_command(args),
        input=admin_sql,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=mysql_env(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if created.returncode != 0:
        raise RuntimeError(f"Cannot initialize benchmark database: {created.stdout}")

    results = []
    for name in SCHEMA_SCRIPTS:
        path = args.sql_root / name
        started = time.perf_counter()
        with path.open("r", encoding="utf-8-sig") as handle:
            completed = subprocess.run(
                mysql_command(args, database),
                stdin=handle,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=mysql_env(args),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
        item = {
            "file": name,
            "sha256": sha256_file(path),
            "elapsedSeconds": round(time.perf_counter() - started, 6),
            "exitCode": completed.returncode,
            "outputTail": (completed.stdout or "").splitlines()[-40:],
        }
        results.append(item)
        if completed.returncode != 0:
            raise RuntimeError(f"SQL import failed for {name}: {completed.stdout}")
    return results


class Backend:
    def __init__(self, args, database: str, port: int, runtime_root: Path):
        self.args = args
        self.database = database
        self.port = port
        self.runtime_root = runtime_root
        self.stdout_path = runtime_root / f"backend-{port}.log"
        self.process: subprocess.Popen[str] | None = None

    def start(self) -> None:
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update(
            {
                "DB_URL": f"jdbc:mysql://{self.args.db_host}:{self.args.db_port}/{self.database}?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai&useSSL=false",
                "DB_USERNAME": self.args.db_user,
                "DB_PASSWORD": self.args.db_password,
                "SERVER_PORT": str(self.port),
                "SHM_EM_PROFILE": "reproduce",
                "SPRING_PROFILES_ACTIVE": "reproduce",
                "SHM_EM_REPORT_OUTPUT_DIR": str(self.runtime_root / "reports"),
            }
        )
        handle = self.stdout_path.open("w", encoding="utf-8", newline="\n")
        self.process = subprocess.Popen(
            [str(self.args.java), "-jar", str(self.args.backend_jar)],
            cwd=str(self.runtime_root),
            env=env,
            text=True,
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
        handle.close()
        deadline = time.time() + 90
        while time.time() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"Backend exited early; see {self.stdout_path}")
            try:
                response = api_request(self.port, "GET", "/api/em/projects?limit=1")
                if response.get("code") == 0:
                    return
            except Exception:
                time.sleep(0.5)
        raise TimeoutError(f"Backend did not become ready on port {self.port}")

    def stop(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)


def api_request(port: int, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            value = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {path}: {detail}") from exc
    if value.get("code") != 0:
        raise RuntimeError(f"API failure {method} {path}: {value}")
    return value


def time_api(port: int, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[float, dict[str, Any]]:
    started = time.perf_counter_ns()
    response = api_request(port, method, path, payload)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return elapsed_ms, response


def run_api_repetitions(
    port: int,
    operation: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
    validate,
    warmups: int,
    measured: int,
    context: dict[str, Any] | None = None,
    progress_path: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    progress: dict[str, Any] = {"schemaVersion": "shm-em-phase2a-api-progress-v1", "events": []}
    if progress_path is not None and progress_path.is_file():
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
    phases = [("first", 1), ("warmup", warmups), ("measured", measured)]
    for phase, count in phases:
        for index in range(1, count + 1):
            progress_event = {
                "operation": operation,
                "phase": phase,
                "repetition": index,
                "status": "started",
                "startedAt": utc_iso(),
                **(context or {}),
            }
            progress["events"].append(progress_event)
            if progress_path is not None:
                write_json(progress_path, progress)
            started_ns = time.perf_counter_ns()
            try:
                elapsed, response = time_api(port, method, path, payload)
            except Exception as exc:
                progress_event.update(
                    {
                        "status": "failed",
                        "finishedAt": utc_iso(),
                        "elapsedMs": round((time.perf_counter_ns() - started_ns) / 1_000_000, 6),
                        "errorType": type(exc).__name__,
                        "error": str(exc),
                    }
                )
                if progress_path is not None:
                    write_json(progress_path, progress)
                raise
            validation = validate(response)
            if validation.get("pass") is not True:
                raise RuntimeError(f"{operation} returned invalid response: {validation}")
            progress_event.update(
                {
                    "status": "completed",
                    "finishedAt": utc_iso(),
                    "elapsedMs": round(elapsed, 6),
                }
            )
            if progress_path is not None:
                write_json(progress_path, progress)
            rows.append(
                {
                    "operation": operation,
                    "phase": phase,
                    "repetition": index,
                    "elapsedMs": round(elapsed, 6),
                    "httpCode": 200,
                    **(context or {}),
                    **validation,
                }
            )
    measured_values = [row["elapsedMs"] for row in rows if row["phase"] == "measured"]
    return rows, {"operation": operation, "firstMs": rows[0]["elapsedMs"], **summary(measured_values)}


def package_versions(names: Iterable[str]) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for name in names:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def windows_hardware() -> dict[str, Any]:
    if os.name != "nt":
        return {"cpu": "unknown", "physicalCores": "unknown", "logicalCores": os.cpu_count(), "ramBytes": "unknown", "storage": "unknown"}
    script = (
        "$cpu=Get-CimInstance Win32_Processor|Select-Object -First 1 Name,NumberOfCores,NumberOfLogicalProcessors;"
        "$mem=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory;"
        "$disk=Get-PhysicalDisk|Select-Object FriendlyName,MediaType,BusType,Size;"
        "@{cpu=$cpu.Name;physicalCores=$cpu.NumberOfCores;logicalCores=$cpu.NumberOfLogicalProcessors;ramBytes=[int64]$mem;storage=$disk}|ConvertTo-Json -Depth 5 -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        if completed.returncode == 0:
            return json.loads(completed.stdout)
    except Exception:
        pass
    return {"cpu": "unknown", "physicalCores": "unknown", "logicalCores": os.cpu_count(), "ramBytes": "unknown", "storage": "unknown"}


def git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=str(repo),
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


def core_diff(repo: Path) -> dict[str, Any]:
    names = git(repo, "diff", "--name-only", FINAL_CORE_FREEZE_V2, "--", *FROZEN_PATHS).splitlines()
    return {
        "baseline": FINAL_CORE_FREEZE_V2,
        "paths": list(FROZEN_PATHS),
        "modifiedFiles": [item for item in names if item],
        "pass": not any(names),
    }


def collect_environment(args, database: str) -> dict[str, Any]:
    db = Database(args, database)
    try:
        mysql = db.one(
            "SELECT VERSION() AS version, @@innodb_buffer_pool_size AS innodbBufferPoolSize, "
            "@@max_connections AS maxConnections, @@default_storage_engine AS defaultStorageEngine, "
            "@@innodb_flush_log_at_trx_commit AS innodbFlushLogAtTrxCommit, "
            "@@transaction_isolation AS transactionIsolation"
        )
    finally:
        db.close()
    return {
        "schemaVersion": "shm-em-phase2a-environment-v1",
        "capturedAt": utc_iso(),
        "os": {"platform": platform.platform(), "system": platform.system(), "release": platform.release(), "version": platform.version()},
        "hardware": windows_hardware(),
        "runtime": {
            "python": platform.python_version(),
            "pythonImplementation": platform.python_implementation(),
            "packages": package_versions(("torch", "numpy", "pandas", "PyMySQL", "scikit-learn", "joblib")),
            "java": command_version([str(args.java), "-version"], args.repo_root),
            "maven": command_version([str(args.maven), "-version"], args.repo_root),
            "node": command_version(["node", "--version"], args.repo_root),
            "npm": command_version([str(args.npm), "--version"], args.repo_root),
        },
        "mysql": mysql,
        "mysqlClient": command_version([str(args.mysql), "--version"], args.repo_root),
        "git": {
            "head": git(args.repo_root, "rev-parse", "HEAD"),
            "branch": git(args.repo_root, "branch", "--show-current"),
            "phase1bCommit": PHASE1B_COMMIT,
            "coreFreezeSha": FINAL_CORE_FREEZE_V2,
        },
        "benchmark": {
            "database": database,
            "concurrency": 1,
            "cachePolicy": "application steady-state/warm-cache; first call retained separately; OS page cache not flushed",
        },
    }


def table_storage(db: Database) -> list[dict[str, Any]]:
    names = (
        "em_prediction_result",
        "em_prediction_run",
        "em_prediction_batch",
        "em_prediction_execution_gate",
    )
    with db.connection.cursor() as cursor:
        for name in names:
            cursor.execute(f"ANALYZE TABLE `{name}`")
    placeholders = ",".join(["%s"] * len(names))
    return db.all(
        f"SELECT table_name, engine, table_rows, data_length, index_length, data_free "
        f"FROM information_schema.tables WHERE table_schema=%s AND table_name IN ({placeholders}) "
        "ORDER BY table_name",
        (db.database, *names),
    )


def manifest_for(root: Path, manifest_name: str) -> dict[str, Any]:
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or path.name == manifest_name or "gpt-review-package" in relative.parts:
            continue
        files.append(
            {
                "path": relative.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schemaVersion": "shm-em-phase2a-manifest-v1",
        "coreFreezeSha": FINAL_CORE_FREEZE_V2,
        "phase1bCommit": PHASE1B_COMMIT,
        "generatedAt": utc_iso(),
        "fileCountExcludingManifest": len(files),
        "files": files,
    }


def resolve_common_args(parser):
    repo = Path(__file__).resolve().parents[2]
    parser.add_argument("--db-host", default="127.0.0.1")
    parser.add_argument("--db-port", type=int, default=3306)
    parser.add_argument("--db-user", default="root")
    parser.add_argument("--db-password", default=os.environ.get("DB_ADMIN_PASSWORD"))
    parser.add_argument("--mysql", type=Path, default=Path(r"D:\Tools\mysql-8.0.41\bin\mysql.exe"))
    parser.add_argument("--python", type=Path, default=Path(r"D:\anaconda3\envs\py310\python.exe"))
    parser.add_argument("--java", type=Path, default=Path(r"C:\Users\nlfdz\.jdks\temurin-1.8.0_482\bin\java.exe"))
    parser.add_argument("--maven", type=Path, default=Path(r"D:\Tools\apache-maven-3.9.16\bin\mvn.cmd"))
    parser.add_argument("--npm", type=Path, default=Path("npm.cmd"))
    args = parser.parse_args()
    if not args.db_password:
        parser.error("Set DB_ADMIN_PASSWORD; credentials are never written to evidence")
    args.repo_root = repo
    args.sql_root = repo / "sql/shm_em_database"
    args.backend_root = repo / "src/backend"
    args.frontend_root = repo / "src/frontend"
    args.pit_pre_root = repo / "src/pit_pre"
    args.evidence_root = repo / "artifacts/revision/benchmarks"
    args.runtime_root = Path(tempfile.mkdtemp(prefix="shm-em-phase2a-"))
    jars = sorted(
        args.backend_root.joinpath("target").glob("*.jar"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    args.backend_jar = next((item for item in jars if not item.name.endswith(".original")), None)
    for executable in (args.mysql, args.python, args.java, args.maven):
        if not executable.is_file():
            parser.error(f"Executable not found: {executable}")
    if args.backend_jar is None:
        parser.error("Backend jar is missing; run the backend package build first")
    return args


def cleanup_runtime(args) -> None:
    shutil.rmtree(args.runtime_root, ignore_errors=True)
