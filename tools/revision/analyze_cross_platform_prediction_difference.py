#!/usr/bin/env python3
"""Quantify persisted prediction differences after an exact output-hash stop."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
from typing import Any

import pymysql

from validate_compose_reference import ComposeDatabase


NUMERIC_FIELDS = (
    "raw_predicted_value",
    "predicted_value",
    "engineering_value",
    "lower_bound",
    "upper_bound",
    "engineering_lower_bound",
    "engineering_upper_bound",
    "confidence",
)
CATEGORICAL_FIELDS = (
    "raw_predicted_unit",
    "predicted_unit",
    "engineering_metric_code",
    "engineering_unit",
    "conversion_operator_code",
    "conversion_version",
    "conversion_status",
    "quality_flag",
)
SELECT_FIELDS = ("model_code", "target_type", "feature_code", "step", *NUMERIC_FIELDS, *CATEGORICAL_FIELDS)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows-host", default="127.0.0.1")
    parser.add_argument("--windows-port", type=int, default=3306)
    parser.add_argument("--windows-user", default="root")
    parser.add_argument("--windows-password-env", default="SHM_EM_WINDOWS_DB_PASSWORD")
    parser.add_argument("--windows-database", default="shm_em_reproduce_benchmark_reference")
    parser.add_argument("--windows-batch-id", type=int, default=40)
    parser.add_argument("--linux-batch-id", type=int, default=5)
    parser.add_argument("--compose-file", type=Path, default=Path("compose.yaml"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/revision/portability/cross-platform-numeric-difference.json"))
    return parser.parse_args()


def sql(batch_id: int) -> str:
    fields = ",".join(f"p.{field}" if field != "model_code" else "r.model_code" for field in SELECT_FIELDS)
    return (
        f"SELECT {fields} FROM em_prediction_result p "
        f"JOIN em_prediction_run r ON r.id=p.run_id WHERE p.batch_id={batch_id};"
    )


def normalize(value: Any) -> str | None:
    if value is None or value == "NULL":
        return None
    return str(value)


def windows_rows(args: argparse.Namespace) -> list[dict[str, str | None]]:
    password = os.environ.get(args.windows_password_env)
    if not password:
        raise SystemExit(f"Set {args.windows_password_env}; its value is never written to evidence")
    connection = pymysql.connect(
        host=args.windows_host,
        port=args.windows_port,
        user=args.windows_user,
        password=password,
        database=args.windows_database,
        charset="utf8mb4",
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql(args.windows_batch_id))
            return [dict(zip(SELECT_FIELDS, (normalize(value) for value in row))) for row in cursor.fetchall()]
    finally:
        connection.close()


def linux_rows(db: ComposeDatabase, batch_id: int) -> list[dict[str, str | None]]:
    lines = db.query(sql(batch_id)).splitlines()
    result = []
    for line in lines:
        values = line.split("\t")
        if len(values) != len(SELECT_FIELDS):
            raise RuntimeError(f"Unexpected Compose row field count: {len(values)}")
        result.append(dict(zip(SELECT_FIELDS, (normalize(value) for value in values))))
    return result


def key(row: dict[str, str | None]) -> tuple[str, str, int]:
    return (str(row["target_type"]), str(row["feature_code"]), int(str(row["step"])))


def decimal(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def main() -> int:
    args = arguments()
    repo = Path(__file__).resolve().parents[2]
    compose = ComposeDatabase(repo, (repo / args.compose_file).resolve())
    windows = {key(row): row for row in windows_rows(args)}
    linux = {key(row): row for row in linux_rows(compose, args.linux_batch_id)}
    common = sorted(windows.keys() & linux.keys())
    missing_linux = sorted(windows.keys() - linux.keys())
    unexpected_linux = sorted(linux.keys() - windows.keys())

    field_summary: dict[str, dict[str, Any]] = {}
    model_summary: dict[str, dict[str, Any]] = {}
    top: list[dict[str, Any]] = []
    categorical_differences = 0
    for field in NUMERIC_FIELDS:
        differences = 0
        max_abs = Decimal(0)
        max_rel = Decimal(0)
        for row_key in common:
            baseline = decimal(windows[row_key][field])
            actual = decimal(linux[row_key][field])
            if baseline is None or actual is None:
                if baseline != actual:
                    differences += 1
                continue
            absolute = abs(actual - baseline)
            denominator = abs(baseline)
            relative = absolute / denominator if denominator else (Decimal(0) if absolute == 0 else Decimal("Infinity"))
            if absolute:
                differences += 1
                model = str(windows[row_key]["model_code"])
                summary = model_summary.setdefault(model, {"differingValues": 0, "maxAbsoluteDifference": Decimal(0), "maxRelativeDifference": Decimal(0)})
                summary["differingValues"] += 1
                summary["maxAbsoluteDifference"] = max(summary["maxAbsoluteDifference"], absolute)
                summary["maxRelativeDifference"] = max(summary["maxRelativeDifference"], relative)
                top.append({
                    "modelCode": model,
                    "targetType": row_key[0],
                    "featureCode": row_key[1],
                    "step": row_key[2],
                    "field": field,
                    "windowsValue": str(baseline),
                    "linuxValue": str(actual),
                    "absoluteDifference": str(absolute),
                    "relativeDifference": str(relative),
                })
            max_abs = max(max_abs, absolute)
            max_rel = max(max_rel, relative)
        field_summary[field] = {"differingRows": differences, "maxAbsoluteDifference": str(max_abs), "maxRelativeDifference": str(max_rel)}

    for row_key in common:
        categorical_differences += sum(windows[row_key][field] != linux[row_key][field] for field in CATEGORICAL_FIELDS)

    for model, item in model_summary.items():
        item["maxAbsoluteDifference"] = str(item["maxAbsoluteDifference"])
        item["maxRelativeDifference"] = str(item["maxRelativeDifference"])
    top.sort(key=lambda item: Decimal(item["absoluteDifference"]), reverse=True)

    linux_evidence = json.loads((repo / "artifacts/revision/portability/linux-reference-reproduction.json").read_text(encoding="utf-8"))
    exact = linux_evidence["predictionOutputHash"] == linux_evidence["expectedPredictionOutputHash"]
    result = {
        "schemaVersion": "shm-em-phase2c-cross-platform-numeric-difference-v1",
        "capturedAtUtc": datetime.now(timezone.utc).isoformat(),
        "comparisonBoundary": "Persisted DECIMAL prediction fields after model inference and engineering conversion",
        "windowsBaseline": {"databaseAlias": args.windows_database, "batchId": args.windows_batch_id, "outputHash": linux_evidence["expectedPredictionOutputHash"]},
        "linuxDocker": {"batchId": args.linux_batch_id, "outputHash": linux_evidence["predictionOutputHash"]},
        "rowCoverage": {"windows": len(windows), "linux": len(linux), "matched": len(common), "missingOnLinux": len(missing_linux), "unexpectedOnLinux": len(unexpected_linux)},
        "fieldDifferences": field_summary,
        "modelDifferences": model_summary,
        "categoricalDifferenceCount": categorical_differences,
        "largestPersistedDifferences": top[:20],
        "exactOutputHash": exact,
        "toleranceApplied": False,
        "decision": "PASS" if exact else "STOP_EXACT_CROSS_PLATFORM_REPRODUCTION",
        "interpretation": "Persisted values are rounded to schema precision; pre-persistence floating differences below that precision cannot be reconstructed from the database." if not exact else "Exact output hash matched.",
    }
    output = repo / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"rows": result["rowCoverage"], "fields": field_summary, "models": model_summary, "decision": result["decision"]}, indent=2))
    return 0 if exact else 2


if __name__ == "__main__":
    raise SystemExit(main())
