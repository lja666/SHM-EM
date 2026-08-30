"""Independent Phase 1A.1 reference implementation for persisted forecast hashes."""

from __future__ import annotations

import datetime as dt
import decimal
import hashlib
import json
from typing import Any


RESULT_HASH_VERSION = "prediction-persisted-integrity-v1"
OUTPUT_HASH_VERSION = "prediction-persisted-output-integrity-v1"
FIELDS = (
    "target_type", "feature_code", "project_id", "station_id", "instrument_id",
    "metric_code", "engineering_metric_code", "step", "horizon_minutes",
    "base_time", "future_time", "raw_predicted_value", "raw_predicted_unit",
    "predicted_value", "predicted_unit", "engineering_value", "engineering_unit",
    "lower_bound", "upper_bound", "engineering_lower_bound", "engineering_upper_bound",
    "confidence", "conversion_operator_code", "conversion_version", "conversion_status",
    "quality_flag", "source_record_key",
)
DECIMAL_SCALES = {
    "raw_predicted_value": 8, "predicted_value": 8, "engineering_value": 8,
    "lower_bound": 8, "upper_bound": 8, "engineering_lower_bound": 8,
    "engineering_upper_bound": 8, "confidence": 6,
}
INTEGER_FIELDS = {"project_id", "station_id", "instrument_id", "step", "horizon_minutes"}
DATETIME_FIELDS = {"base_time", "future_time"}


def result_hash(rows: list[dict[str, Any]]) -> str:
    rows = sorted(
        rows,
        key=lambda row: (
            str(row.get("feature_code") or ""),
            int(row.get("step") or 0),
            str(row.get("source_record_key") or ""),
        ),
    )
    lines = [RESULT_HASH_VERSION]
    for row in rows:
        values = [canonical_value(field, row.get(field)) for field in FIELDS]
        lines.append(json.dumps(values, ensure_ascii=False, separators=(",", ":")))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def output_hash(run_hashes: dict[str, str]) -> str:
    lines = [OUTPUT_HASH_VERSION]
    lines.extend(
        json.dumps([key, run_hashes[key]], ensure_ascii=False, separators=(",", ":"))
        for key in sorted(run_hashes)
    )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def canonical_value(field: str, value: Any) -> str | None:
    if value is None:
        return None
    if field in DECIMAL_SCALES:
        return format(decimal.Decimal(str(value)), f".{DECIMAL_SCALES[field]}f")
    if field in DATETIME_FIELDS:
        if isinstance(value, str):
            value = dt.datetime.fromisoformat(value)
        return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23]
    if field in INTEGER_FIELDS:
        return str(int(value))
    return str(value)


def recompute_batch(db, batch_id: int) -> dict[str, Any]:
    runs = db.all(
        "SELECT id,model_code,model_version,result_hash FROM em_prediction_run "
        "WHERE batch_id=%s ORDER BY model_code,model_version,id",
        (batch_id,),
    )
    run_hashes: dict[str, str] = {}
    for run in runs:
        rows = db.all(
            "SELECT " + ",".join(FIELDS) + " FROM em_prediction_result "
            "WHERE run_id=%s ORDER BY feature_code,step,source_record_key",
            (run["id"],),
        )
        calculated = result_hash(rows)
        model_key = f"{run['model_code']}@{run['model_version']}"
        if model_key in run_hashes:
            raise RuntimeError(f"Duplicate run model key in batch {batch_id}: {model_key}")
        run_hashes[model_key] = calculated
        db.execute(
            "UPDATE em_prediction_run SET persisted_result_hash=%s, "
            "persisted_result_hash_version=%s WHERE id=%s",
            (calculated, RESULT_HASH_VERSION, run["id"]),
        )
    aggregate = output_hash(run_hashes)
    db.execute(
        "UPDATE em_prediction_batch SET persisted_output_hash=%s, "
        "persisted_output_hash_version=%s WHERE id=%s",
        (aggregate, OUTPUT_HASH_VERSION, batch_id),
    )
    return {
        "batchId": batch_id,
        "runCount": len(runs),
        "runHashes": run_hashes,
        "persistedOutputHash": aggregate,
    }
