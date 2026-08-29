#!/usr/bin/env python3
"""Read-only audit of PIT_PRE input alignment against the public SQL sample.

The audit reproduces the production alignment and fill sequence without
connecting to MySQL, mutating source data, or running model inference.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from statistics import median
from typing import Any, Iterable

import joblib
import pandas as pd


PROJECT_CODE = "SHM_EM_PUBLIC_SAMPLE"
SCHEMA_VERSION = "pit_pre_v1"
ALLOWED_VALUE_COLUMNS = {"raw_value", "metric_value", "baseline_value"}
ALLOWED_OBSERVATION_TABLES = {
    "em_obs_displacement",
    "em_obs_earth_pressure",
    "em_obs_pressure_water_level",
    "em_obs_static_level",
}
AUDIT_TABLES = {
    "em_project",
    "em_metric",
    "em_prediction_model",
    "em_prediction_feature_mapping",
    "em_observation_table_registry",
    *ALLOWED_OBSERVATION_TABLES,
}
CSV_COLUMNS = [
    "model_code",
    "feature_code",
    "source_table",
    "source_metric",
    "history_window_size",
    "raw_sample_count",
    "exact_timestamp_match_count",
    "backward_asof_match_count",
    "interior_interpolation_count",
    "leading_boundary_extension_count",
    "trailing_boundary_extension_count",
    "forward_fill_count",
    "backward_fill_count",
    "final_missing_count",
    "max_raw_gap_seconds",
    "median_absolute_source_offset_seconds",
    "p95_absolute_source_offset_seconds",
    "max_absolute_source_offset_seconds",
    "past_source_cell_count",
    "future_source_cell_count",
    "past_source_contributor_count",
    "future_source_contributor_count",
    "max_past_source_lag_seconds",
    "max_future_source_lead_seconds",
    "exact_match_ratio",
    "asof_alignment_ratio",
    "non_exact_alignment_ratio",
    "fill_ratio",
]


@dataclass(frozen=True)
class Feature:
    feature_code: str
    training_feature_code: str
    source_table: str
    source_metric: str
    source_value_column: str
    station_id: int | None
    instrument_id: int | None


def parse_args() -> argparse.Namespace:
    script = Path(__file__).resolve()
    root = script.parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=root)
    parser.add_argument(
        "--sample-sql",
        type=Path,
        default=Path("sql/shm_em_database/02_SHM_EM_public_sample.sql"),
    )
    parser.add_argument("--project-code", default=PROJECT_CODE)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/revision/phase0_6_1"),
    )
    return parser.parse_args()


def repo_path(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _tuple_payloads(values: str) -> Iterable[str]:
    start: int | None = None
    quoted = False
    escaped = False
    depth = 0
    for index, char in enumerate(values):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "'":
                quoted = False
            continue
        if char == "'":
            quoted = True
        elif char == "(":
            if depth == 0:
                start = index + 1
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0 and start is not None:
                yield values[start:index]
                start = None
    if quoted or depth != 0:
        raise ValueError("Malformed INSERT tuple list in public sample")


def _sql_value(token: str) -> Any:
    value = token.strip()
    if value.upper() == "NULL":
        return None
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+)(?:[eE][-+]?\d+)?", value):
        return float(value)
    return value


def parse_public_sample(path: Path) -> dict[str, list[dict[str, Any]]]:
    tables: dict[str, list[dict[str, Any]]] = {name: [] for name in AUDIT_TABLES}
    with path.open("r", encoding="utf-8-sig") as stream:
        for line_no, line in enumerate(stream, start=1):
            if not line.startswith("INSERT INTO `"):
                continue
            header, separator, values = line.rstrip("\r\n").partition(") VALUES ")
            if not separator:
                continue
            match = re.match(r"INSERT INTO `([^`]+)` \((.*)$", header)
            if not match:
                raise ValueError(f"Cannot parse INSERT header at line {line_no}")
            table = match.group(1)
            if table not in tables:
                continue
            columns = [part.strip().strip("`") for part in match.group(2).split(",")]
            value_text = values[:-1] if values.endswith(";") else values
            for payload in _tuple_payloads(value_text):
                parsed = next(
                    csv.reader(
                        [payload],
                        delimiter=",",
                        quotechar="'",
                        escapechar="\\",
                        doublequote=True,
                        skipinitialspace=True,
                    )
                )
                if len(parsed) != len(columns):
                    raise ValueError(
                        f"Column/value mismatch for {table} at line {line_no}: "
                        f"{len(columns)} columns, {len(parsed)} values"
                    )
                tables[table].append(dict(zip(columns, map(_sql_value, parsed))))
    return tables


def nullable_int(value: Any) -> int | None:
    return None if value is None else int(value)


def load_contract(
    root: Path,
    tables: dict[str, list[dict[str, Any]]],
    project_code: str,
) -> tuple[list[dict[str, Any]], list[Feature], int]:
    project = next(
        (row for row in tables["em_project"] if row.get("project_code") == project_code),
        None,
    )
    if project is None:
        raise ValueError(f"Project {project_code} is absent from the public sample")
    project_id = int(project["id"])

    models = [
        dict(row)
        for row in tables["em_prediction_model"]
        if int(row["project_id"]) == project_id and row.get("status") == "active"
    ]
    if not models:
        raise ValueError(f"No active models found for {project_code}")
    models.sort(key=lambda row: (str(row["model_code"]), int(row["id"])))

    registries = {
        str(row["registry_code"]): row
        for row in tables["em_observation_table_registry"]
        if int(row["project_id"]) == project_id
        and int(row.get("enabled") or 0) == 1
        and int(row.get("is_queryable") or 0) == 1
    }
    mappings = [
        row
        for row in tables["em_prediction_feature_mapping"]
        if int(row["project_id"]) == project_id
        and row.get("schema_version") == SCHEMA_VERSION
        and int(row.get("enabled") or 0) == 1
        and (row.get("feature_role") or "model_input") == "model_input"
    ]
    mappings.sort(key=lambda row: (int(row["feature_order"]), int(row["id"])))

    features: list[Feature] = []
    for row in mappings:
        registry_code = str(row.get("source_registry_code") or "").strip()
        registry = registries.get(registry_code)
        if registry is None:
            raise ValueError(f"Enabled feature {row['feature_code']} has no queryable registry")
        source_table = str(registry.get("physical_table_name") or "").strip()
        if source_table not in ALLOWED_OBSERVATION_TABLES:
            raise ValueError(f"Unsupported production observation table: {source_table}")
        source_value_column = str(
            row.get("source_value_column")
            or row.get("source_field")
            or "metric_value"
        ).strip()
        if source_value_column not in ALLOWED_VALUE_COLUMNS:
            raise ValueError(f"Unsupported production value column: {source_value_column}")
        station_id = nullable_int(row.get("station_id"))
        instrument_id = nullable_int(row.get("instrument_id"))
        if station_id is None and instrument_id is None:
            raise ValueError(f"Feature {row['feature_code']} has no station or instrument identity")
        features.append(
            Feature(
                feature_code=str(row["feature_code"]),
                training_feature_code=str(
                    row.get("training_feature_code") or row.get("feature_code")
                ),
                source_table=source_table,
                source_metric=str(row["source_metric_code"]),
                source_value_column=source_value_column,
                station_id=station_id,
                instrument_id=instrument_id,
            )
        )

    duplicate_codes = pd.Series([item.training_feature_code for item in features]).duplicated()
    if duplicate_codes.any():
        raise ValueError("Active feature mappings contain duplicate training_feature_code values")

    for model in models:
        preprocessor_uri = str(model["preprocessor_uri"])
        preprocessor_path = root / "src/pit_pre" / preprocessor_uri
        if not preprocessor_path.is_file():
            raise FileNotFoundError(f"Missing frozen preprocessor: {preprocessor_uri}")
        preprocessor = joblib.load(preprocessor_path)
        model["input_columns"] = [str(value) for value in preprocessor["input_columns"]]
        model["runtime"] = json.loads(str(model["runtime_config_json"]))
    return models, features, project_id


def feature_rows(
    feature: Feature,
    tables: dict[str, list[dict[str, Any]]],
    project_id: int,
) -> pd.DataFrame:
    rows = []
    for row in tables[feature.source_table]:
        if int(row["project_id"]) != project_id:
            continue
        if row.get("metric_code") != feature.source_metric:
            continue
        if feature.station_id is not None and int(row["station_id"]) != feature.station_id:
            continue
        if feature.instrument_id is not None and int(row["instrument_id"]) != feature.instrument_id:
            continue
        value = row.get(feature.source_value_column)
        if value is None:
            continue
        rows.append(
            {
                "measurement_time": pd.Timestamp(row["observed_at"]),
                "value": float(value),
                "id": int(row["id"]),
            }
        )
    if not rows:
        return pd.DataFrame(columns=["measurement_time", "value", "id"])
    return pd.DataFrame(rows).sort_values(["measurement_time", "id"]).reset_index(drop=True)


def aligned_trace(
    series: pd.DataFrame,
    time_index: list[pd.Timestamp],
    tolerance: pd.Timedelta,
) -> pd.DataFrame:
    target = pd.DataFrame({"time": pd.to_datetime(time_index)})
    if series.empty:
        target["value"] = math.nan
        target["stage"] = "missing"
        target["lineage"] = [tuple() for _ in range(len(target))]
        return target

    data = (
        series.sort_values(["measurement_time", "id"])
        .drop_duplicates("measurement_time", keep="last")
        .dropna(subset=["value"])
        .copy()
    )
    data["source_time"] = pd.to_datetime(data["measurement_time"])
    merged = pd.merge_asof(
        target,
        data[["source_time", "value"]].rename(columns={"source_time": "match_time"}),
        left_on="time",
        right_on="match_time",
        direction="backward",
        tolerance=tolerance,
    )
    initial = pd.to_numeric(merged["value"], errors="coerce")
    stages: list[str] = []
    lineage: list[tuple[pd.Timestamp, ...]] = []
    for target_time, match_time, value in zip(merged["time"], merged["match_time"], initial):
        if pd.isna(value) or pd.isna(match_time):
            stages.append("missing")
            lineage.append(tuple())
        elif target_time == match_time:
            stages.append("exact_timestamp_match")
            lineage.append((pd.Timestamp(match_time),))
        else:
            stages.append("backward_asof")
            lineage.append((pd.Timestamp(match_time),))

    interpolated = initial.interpolate(method="linear", limit_direction="both")
    populated_positions = [index for index, value in enumerate(initial) if pd.notna(value)]
    for index, (before, after) in enumerate(zip(initial, interpolated)):
        if pd.notna(before) or pd.isna(after):
            continue
        previous = [position for position in populated_positions if position < index]
        following = [position for position in populated_positions if position > index]
        contributors: list[pd.Timestamp] = []
        if previous:
            contributors.extend(lineage[previous[-1]])
        if following:
            contributors.extend(lineage[following[0]])
        if previous and following:
            stages[index] = "interior_interpolation"
        elif following:
            stages[index] = "leading_boundary_extension"
        elif previous:
            stages[index] = "trailing_boundary_extension"
        else:
            stages[index] = "missing"
        lineage[index] = tuple(dict.fromkeys(contributors))

    forward = interpolated.ffill()
    for index, (before, after) in enumerate(zip(interpolated, forward)):
        if pd.notna(before) or pd.isna(after):
            continue
        previous = next((position for position in range(index - 1, -1, -1) if pd.notna(forward.iloc[position])), None)
        stages[index] = "forward_fill"
        lineage[index] = tuple() if previous is None else lineage[previous]

    backward = forward.bfill()
    for index, (before, after) in enumerate(zip(forward, backward)):
        if pd.notna(before) or pd.isna(after):
            continue
        following = next((position for position in range(index + 1, len(backward)) if pd.notna(backward.iloc[position])), None)
        stages[index] = "backward_fill"
        lineage[index] = tuple() if following is None else lineage[following]

    for index, value in enumerate(backward):
        if pd.isna(value):
            stages[index] = "missing"
            lineage[index] = tuple()
    target["value"] = backward
    target["stage"] = stages
    target["lineage"] = lineage
    return target


def max_gap_seconds(series: pd.DataFrame) -> float | None:
    timestamps = (
        series.sort_values(["measurement_time", "id"])
        .drop_duplicates("measurement_time", keep="last")["measurement_time"]
        .sort_values()
    )
    if len(timestamps) < 2:
        return None
    return float(timestamps.diff().dropna().dt.total_seconds().max())


def source_offset_groups(trace: pd.DataFrame) -> list[tuple[float, ...]]:
    groups: list[tuple[float, ...]] = []
    for target_time, lineage in zip(trace["time"], trace["lineage"]):
        groups.append(tuple(
            float((pd.Timestamp(target_time) - source_time).total_seconds())
            for source_time in lineage
        ))
    return groups


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    return float(pd.Series(values, dtype="float64").quantile(quantile))


def rounded(value: float | None, digits: int = 6) -> float | None:
    return None if value is None or math.isnan(value) else round(float(value), digits)


def audit_alignment(
    root: Path,
    tables: dict[str, list[dict[str, Any]]],
    models: list[dict[str, Any]],
    features: list[Feature],
    project_id: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    feature_by_code = {item.training_feature_code: item for item in features}
    series_by_code = {
        item.training_feature_code: feature_rows(item, tables, project_id)
        for item in features
    }
    latest_candidates = [
        series["measurement_time"].max()
        for series in series_by_code.values()
        if not series.empty
    ]
    if len(latest_candidates) != len(features):
        missing = sorted(code for code, series in series_by_code.items() if series.empty)
        raise ValueError(f"Configured features without public observations: {missing}")
    latest_time = min(pd.Timestamp(value) for value in latest_candidates)
    steps = {int(model["time_step_minutes"]) for model in models}
    if len(steps) != 1:
        raise ValueError(f"Active models do not share one time step: {sorted(steps)}")
    step_minutes = next(iter(steps))
    step = pd.Timedelta(minutes=step_minutes)
    max_rows = max(int(model["required_history_rows"]) for model in models)
    full_start = latest_time - step * (max_rows - 1)
    full_index = [full_start + step * index for index in range(max_rows)]

    traces: dict[str, pd.DataFrame] = {}
    query_series: dict[str, pd.DataFrame] = {}
    for feature in features:
        series = series_by_code[feature.training_feature_code]
        queried = series[
            (series["measurement_time"] >= full_start - step)
            & (series["measurement_time"] <= latest_time)
        ].copy()
        query_series[feature.training_feature_code] = queried
        traces[feature.training_feature_code] = aligned_trace(queried, full_index, step)

    rows: list[dict[str, Any]] = []
    model_summaries: list[dict[str, Any]] = []
    all_source_offsets: list[float] = []
    for model in models:
        model_code = str(model["model_code"])
        history_rows = int(model["required_history_rows"])
        unknown = [code for code in model["input_columns"] if code not in feature_by_code]
        if unknown:
            raise ValueError(f"{model_code} preprocessor inputs missing from DB mappings: {unknown}")
        model_rows: list[dict[str, Any]] = []
        model_source_offsets: list[float] = []
        model_start = latest_time - step * (history_rows - 1)
        for training_code in model["input_columns"]:
            feature = feature_by_code[training_code]
            trace = traces[training_code].tail(history_rows).reset_index(drop=True)
            raw = query_series[training_code]
            raw_window = raw[
                (raw["measurement_time"] >= model_start - step)
                & (raw["measurement_time"] <= latest_time)
            ]
            counts = trace["stage"].value_counts().to_dict()
            exact = int(counts.get("exact_timestamp_match", 0))
            asof = int(counts.get("backward_asof", 0))
            interior = int(counts.get("interior_interpolation", 0))
            leading = int(counts.get("leading_boundary_extension", 0))
            trailing = int(counts.get("trailing_boundary_extension", 0))
            forward = int(counts.get("forward_fill", 0))
            backward = int(counts.get("backward_fill", 0))
            missing = int(counts.get("missing", 0))
            fill = interior + leading + trailing + forward + backward
            non_exact = sum(
                int(counts.get(stage, 0))
                for stage in (
                    "backward_asof",
                    "interior_interpolation",
                    "leading_boundary_extension",
                    "trailing_boundary_extension",
                    "forward_fill",
                    "backward_fill",
                )
            )
            offset_groups = source_offset_groups(trace)
            offsets = [offset for group in offset_groups for offset in group]
            absolute_offsets = [abs(offset) for offset in offsets]
            past_offsets = [offset for offset in offsets if offset > 0]
            future_offsets = [-offset for offset in offsets if offset < 0]
            model_source_offsets.extend(offsets)
            all_source_offsets.extend(offsets)
            row = {
                "model_code": model_code,
                "feature_code": feature.feature_code,
                "source_table": feature.source_table,
                "source_metric": feature.source_metric,
                "history_window_size": history_rows,
                "raw_sample_count": len(raw_window),
                "exact_timestamp_match_count": exact,
                "backward_asof_match_count": asof,
                "interior_interpolation_count": interior,
                "leading_boundary_extension_count": leading,
                "trailing_boundary_extension_count": trailing,
                "forward_fill_count": forward,
                "backward_fill_count": backward,
                "final_missing_count": missing,
                "max_raw_gap_seconds": rounded(max_gap_seconds(raw_window), 3),
                "median_absolute_source_offset_seconds": rounded(percentile(absolute_offsets, 0.5), 3),
                "p95_absolute_source_offset_seconds": rounded(percentile(absolute_offsets, 0.95), 3),
                "max_absolute_source_offset_seconds": rounded(max(absolute_offsets), 3) if absolute_offsets else None,
                "past_source_cell_count": sum(any(offset > 0 for offset in group) for group in offset_groups),
                "future_source_cell_count": sum(any(offset < 0 for offset in group) for group in offset_groups),
                "past_source_contributor_count": len(past_offsets),
                "future_source_contributor_count": len(future_offsets),
                "max_past_source_lag_seconds": rounded(max(past_offsets), 3) if past_offsets else None,
                "max_future_source_lead_seconds": rounded(max(future_offsets), 3) if future_offsets else None,
                "exact_match_ratio": rounded(exact / history_rows, 12),
                "asof_alignment_ratio": rounded(asof / history_rows, 12),
                "non_exact_alignment_ratio": rounded(non_exact / history_rows, 12),
                "fill_ratio": rounded(fill / history_rows, 12),
            }
            rows.append(row)
            model_rows.append(row)

        fill_ratios = [float(item["fill_ratio"]) for item in model_rows]
        non_exact_ratios = [float(item["non_exact_alignment_ratio"]) for item in model_rows]
        gaps = [float(item["max_raw_gap_seconds"]) for item in model_rows if item["max_raw_gap_seconds"] is not None]
        model_summaries.append(
            {
                "modelCode": model_code,
                "featureCount": len(model_rows),
                "historyWindowSize": history_rows,
                "backwardAsofFeatureCount": sum(item["backward_asof_match_count"] > 0 for item in model_rows),
                "interiorInterpolationFeatureCount": sum(item["interior_interpolation_count"] > 0 for item in model_rows),
                "boundaryExtensionFeatureCount": sum(
                    item["leading_boundary_extension_count"] > 0
                    or item["trailing_boundary_extension_count"] > 0
                    for item in model_rows
                ),
                "forwardFillFeatureCount": sum(item["forward_fill_count"] > 0 for item in model_rows),
                "backwardFillFeatureCount": sum(item["backward_fill_count"] > 0 for item in model_rows),
                "inputCellCount": history_rows * len(model_rows),
                "exactCellCount": sum(item["exact_timestamp_match_count"] for item in model_rows),
                "asofCellCount": sum(item["backward_asof_match_count"] for item in model_rows),
                "interiorInterpolationCellCount": sum(item["interior_interpolation_count"] for item in model_rows),
                "leadingBoundaryExtensionCellCount": sum(item["leading_boundary_extension_count"] for item in model_rows),
                "trailingBoundaryExtensionCellCount": sum(item["trailing_boundary_extension_count"] for item in model_rows),
                "boundaryExtensionCellCount": sum(
                    item["leading_boundary_extension_count"]
                    + item["trailing_boundary_extension_count"]
                    for item in model_rows
                ),
                "forwardFillCellCount": sum(item["forward_fill_count"] for item in model_rows),
                "backwardFillCellCount": sum(item["backward_fill_count"] for item in model_rows),
                "fillRatio": rounded(sum(
                    item["interior_interpolation_count"]
                    + item["leading_boundary_extension_count"]
                    + item["trailing_boundary_extension_count"]
                    + item["forward_fill_count"]
                    + item["backward_fill_count"]
                    for item in model_rows
                ) / (history_rows * len(model_rows)), 12),
                "nonExactAlignmentRatio": rounded(sum(
                    item["backward_asof_match_count"]
                    + item["interior_interpolation_count"]
                    + item["leading_boundary_extension_count"]
                    + item["trailing_boundary_extension_count"]
                    + item["forward_fill_count"]
                    + item["backward_fill_count"]
                    for item in model_rows
                ) / (history_rows * len(model_rows)), 12),
                "maxFillRatio": rounded(max(fill_ratios)),
                "medianFillRatio": rounded(median(fill_ratios)),
                "maxNonExactAlignmentRatio": rounded(max(non_exact_ratios)),
                "maxRawGapSeconds": rounded(max(gaps), 3) if gaps else None,
                "medianAbsoluteSourceOffsetSeconds": rounded(percentile([abs(value) for value in model_source_offsets], 0.5), 3),
                "p95AbsoluteSourceOffsetSeconds": rounded(percentile([abs(value) for value in model_source_offsets], 0.95), 3),
                "maxAbsoluteSourceOffsetSeconds": rounded(max([abs(value) for value in model_source_offsets]), 3) if model_source_offsets else None,
                "pastSourceCellCount": sum(int(item["past_source_cell_count"]) for item in model_rows),
                "futureSourceCellCount": sum(int(item["future_source_cell_count"]) for item in model_rows),
                "pastSourceContributorCount": sum(int(item["past_source_contributor_count"]) for item in model_rows),
                "futureSourceContributorCount": sum(int(item["future_source_contributor_count"]) for item in model_rows),
                "maxPastSourceLagSeconds": rounded(max(
                    item["max_past_source_lag_seconds"]
                    for item in model_rows
                    if item["max_past_source_lag_seconds"] is not None
                ), 3) if any(item["max_past_source_lag_seconds"] is not None for item in model_rows) else None,
                "maxFutureSourceLeadSeconds": rounded(max(
                    item["max_future_source_lead_seconds"]
                    for item in model_rows
                    if item["max_future_source_lead_seconds"] is not None
                ), 3) if any(item["max_future_source_lead_seconds"] is not None for item in model_rows) else None,
                "unresolvedMissingCount": sum(int(item["final_missing_count"]) for item in model_rows),
            }
        )

    all_fill_ratios = [float(item["fill_ratio"]) for item in rows]
    all_non_exact_ratios = [float(item["non_exact_alignment_ratio"]) for item in rows]
    all_gaps = [float(item["max_raw_gap_seconds"]) for item in rows if item["max_raw_gap_seconds"] is not None]
    summary = {
        "schemaVersion": "shm-em-input-alignment-audit-v3",
        "sourceGitCommit": git_commit(root),
        "projectCode": PROJECT_CODE,
        "auditMode": "offline-read-only-public-sql",
        "productionMethod": [
            "backward_asof",
            "interior_linear_interpolation",
            "leading_or_trailing_boundary_extension",
            "forward_fill",
            "backward_fill",
            "remaining_missing_check",
        ],
        "timeStepMinutes": step_minutes,
        "asofToleranceSeconds": int(step.total_seconds()),
        "commonLatestTime": latest_time.isoformat(),
        "maximumProductionHistoryWindowSize": max_rows,
        "modelCount": len(models),
        "mappedFeatureCount": len(features),
        "auditedModelFeatureCount": len(rows),
        "models": model_summaries,
        "overall": {
            "backwardAsofFeatureCount": sum(item["backward_asof_match_count"] > 0 for item in rows),
            "interiorInterpolationFeatureCount": sum(item["interior_interpolation_count"] > 0 for item in rows),
            "boundaryExtensionFeatureCount": sum(
                item["leading_boundary_extension_count"] > 0
                or item["trailing_boundary_extension_count"] > 0
                for item in rows
            ),
            "forwardFillFeatureCount": sum(item["forward_fill_count"] > 0 for item in rows),
            "backwardFillFeatureCount": sum(item["backward_fill_count"] > 0 for item in rows),
            "inputCellCount": sum(item["history_window_size"] for item in rows),
            "exactCellCount": sum(item["exact_timestamp_match_count"] for item in rows),
            "asofCellCount": sum(item["backward_asof_match_count"] for item in rows),
            "interiorInterpolationCellCount": sum(item["interior_interpolation_count"] for item in rows),
            "leadingBoundaryExtensionCellCount": sum(item["leading_boundary_extension_count"] for item in rows),
            "trailingBoundaryExtensionCellCount": sum(item["trailing_boundary_extension_count"] for item in rows),
            "forwardFillCellCount": sum(item["forward_fill_count"] for item in rows),
            "backwardFillCellCount": sum(item["backward_fill_count"] for item in rows),
            "fillRatio": rounded(sum(
                item["interior_interpolation_count"]
                + item["leading_boundary_extension_count"]
                + item["trailing_boundary_extension_count"]
                + item["forward_fill_count"]
                + item["backward_fill_count"]
                for item in rows
            ) / sum(item["history_window_size"] for item in rows), 12),
            "nonExactAlignmentRatio": rounded(sum(
                item["backward_asof_match_count"]
                + item["interior_interpolation_count"]
                + item["leading_boundary_extension_count"]
                + item["trailing_boundary_extension_count"]
                + item["forward_fill_count"]
                + item["backward_fill_count"]
                for item in rows
            ) / sum(item["history_window_size"] for item in rows), 12),
            "maxFillRatio": rounded(max(all_fill_ratios)),
            "medianFillRatio": rounded(median(all_fill_ratios)),
            "maxNonExactAlignmentRatio": rounded(max(all_non_exact_ratios)),
            "maxRawGapSeconds": rounded(max(all_gaps), 3) if all_gaps else None,
            "medianAbsoluteSourceOffsetSeconds": rounded(percentile([abs(value) for value in all_source_offsets], 0.5), 3),
            "p95AbsoluteSourceOffsetSeconds": rounded(percentile([abs(value) for value in all_source_offsets], 0.95), 3),
            "maxAbsoluteSourceOffsetSeconds": rounded(max([abs(value) for value in all_source_offsets]), 3) if all_source_offsets else None,
            "pastSourceCellCount": sum(int(item["past_source_cell_count"]) for item in rows),
            "futureSourceCellCount": sum(int(item["future_source_cell_count"]) for item in rows),
            "pastSourceContributorCount": sum(int(item["past_source_contributor_count"]) for item in rows),
            "futureSourceContributorCount": sum(int(item["future_source_contributor_count"]) for item in rows),
            "maxPastSourceLagSeconds": rounded(max(
                item["max_past_source_lag_seconds"]
                for item in rows
                if item["max_past_source_lag_seconds"] is not None
            ), 3) if any(item["max_past_source_lag_seconds"] is not None for item in rows) else None,
            "maxFutureSourceLeadSeconds": rounded(max(
                item["max_future_source_lead_seconds"]
                for item in rows
                if item["max_future_source_lead_seconds"] is not None
            ), 3) if any(item["max_future_source_lead_seconds"] is not None for item in rows) else None,
            "unresolvedMissingCount": sum(int(item["final_missing_count"]) for item in rows),
        },
    }
    return rows, summary


def markdown_table(headers: list[str], rows: Iterable[Iterable[Any]]) -> list[str]:
    rendered = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        rendered.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return rendered


def render_policy_review(summary: dict[str, Any]) -> str:
    overall = summary["overall"]
    model_rows = [
        [
            item["modelCode"],
            item["featureCount"],
            item["backwardAsofFeatureCount"],
            item["interiorInterpolationFeatureCount"],
            item["boundaryExtensionFeatureCount"],
            item["forwardFillFeatureCount"],
            item["backwardFillFeatureCount"],
            item["maxRawGapSeconds"],
            item["p95AbsoluteSourceOffsetSeconds"],
            item["futureSourceCellCount"],
            item["maxFutureSourceLeadSeconds"],
            item["maxFillRatio"],
            item["unresolvedMissingCount"],
        ]
        for item in summary["models"]
    ]
    lines = [
        "# SHM-EM Phase 0.6.1 Input Alignment Audit v3",
        "",
        "## Scope and attribution",
        "",
        "This is an offline, read-only audit of the committed public sample. It does not connect to MySQL, modify data, change production inputs, or run model inference. Attribution reproduces the existing three-minute grid, backward `merge_asof`, bidirectional linear interpolation, `ffill`, `bfill`, and remaining-NaN check.",
        "",
        "`fill_ratio` includes interior interpolation, leading/trailing boundary extension, ffill, and bfill, but excludes backward as-of. `non_exact_alignment_ratio` additionally includes backward as-of and describes synchronization to the canonical grid; it is not interpreted as missing-data imputation.",
        "",
        "## Public-sample results",
        "",
        *markdown_table(
            ["Model", "Features", "As-of", "Interior", "Boundary", "FFill", "BFill", "Max gap (s)", "P95 |offset| (s)", "Future cells", "Max lead (s)", "Max fill ratio", "Missing"],
            model_rows,
        ),
        "",
        f"Across `{overall['inputCellCount']}` model-input cells, `{overall['exactCellCount']}` were exact, `{overall['asofCellCount']}` used backward as-of, `{overall['interiorInterpolationCellCount']}` used interior interpolation, and `{overall['leadingBoundaryExtensionCellCount'] + overall['trailingBoundaryExtensionCellCount']}` used boundary extension. Maximum raw gap was `{overall['maxRawGapSeconds']}` seconds, p95 absolute source offset was `{overall['p95AbsoluteSourceOffsetSeconds']}` seconds, `{overall['futureSourceCellCount']}` cells had at least one later-source contributor, maximum future-source lead was `{overall['maxFutureSourceLeadSeconds']}` seconds, maximum fill ratio was `{overall['maxFillRatio']}`, and unresolved missing cells totalled `{overall['unresolvedMissingCount']}`.",
        "",
        "## Required policy questions",
        "",
        "1. **What is the current `merge_asof` tolerance?** One model time step: 180 seconds for the active public-sample contract.",
        "2. **Where is tolerance defined?** `WideTableBuilder` creates `step = timedelta(minutes=time_step_minutes)` and passes that same value to `_align_series` as tolerance.",
        "3. **Is tolerance tied to model sampling interval?** Yes. Active model contracts define `time_step_minutes=3`; contract loading requires a single shared value across active models.",
        "4. **Which features are interpolated?** Every enabled model-input column in the common wide table is included in the DataFrame-wide interpolation operation when it contains a missing grid cell.",
        "5. **Does `limit_direction=\"both\"` allow boundary filling?** Yes. Leading and trailing gaps can be filled from the nearest available boundary value during the interpolation stage.",
        "6. **Can `ffill`/`bfill` spread one point across multiple historical steps?** The sequence permits it in principle. In the audited implementation Pandas' bidirectional interpolation normally fills boundaries first, so the later fill calls only act if values remain. A sparse column can still derive multiple grid cells from one observed value during interpolation.",
        "7. **Are fill counts recorded in production?** Phase 0.6 adds compact descriptive counts to each model run's `input_snapshot_json`; the numerical input remains unchanged.",
        "8. **Is maximum gap recorded in production?** Phase 0.6 records the model-window maximum raw gap as descriptive provenance.",
        "9. **Is there a stale cutoff?** Alignment has a one-step as-of tolerance, but interpolation and boundary filling have no separate temporal-offset cutoff. The execution gate checks completed-batch freshness, not per-feature source offset.",
        "10. **Can the gate use the new diagnostics?** The values are provenance only. Phase 0.6.1 adds no fill, gap, or offset threshold and makes no eligibility decision from them.",
        "11. **Does `input_snapshot_json` record alignment diagnostics?** Yes, as a compact policy/version and per-model quality summary; full feature rows remain revision evidence only.",
        "12. **Can current behavior answer Reviewers 2 and 3?** Yes at the descriptive level: the method, stage counts, fill ratio, raw gap, signed temporal offsets, past lag, and future lead are explicit and reproducible.",
        "13. **What remains deferred?** Scientifically justified acceptance thresholds and gate enforcement. They are not inferred from this single public sample.",
        "",
        "## Phase 0.6.1 conclusion",
        "",
        "Phase 0.6.1 makes source-time direction explicit without changing values, filling behavior, or eligibility. Later-source contributors remain inside the historical window available at the prediction origin; they are not observations beyond the forecast origin. Numerical equivalence is reported separately in the regression artifacts.",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "alignment-audit-v3.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "alignment-audit-v3-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "alignment-audit-v3-review.md").write_text(
        render_policy_review(summary),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    root = args.repo.resolve()
    sample_sql = repo_path(root, args.sample_sql).resolve()
    output_dir = repo_path(root, args.output_dir).resolve()
    if not sample_sql.is_file():
        raise FileNotFoundError(sample_sql)
    tables = parse_public_sample(sample_sql)
    models, features, project_id = load_contract(root, tables, args.project_code)
    rows, summary = audit_alignment(root, tables, models, features, project_id)
    summary["projectCode"] = args.project_code
    summary["publicSample"] = {
        "path": sample_sql.relative_to(root).as_posix(),
        "sha256": sha256(sample_sql),
    }
    write_outputs(output_dir, rows, summary)
    print(json.dumps(summary["overall"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
