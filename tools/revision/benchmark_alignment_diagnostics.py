#!/usr/bin/env python3
"""Benchmark value-only, Phase 0.6 two-pass, and Phase 0.6.1 one-pass alignment."""

from __future__ import annotations

import argparse
import gc
import json
import statistics
import sys
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PIT_PRE_ROOT = ROOT / "src/pit_pre"
if str(PIT_PRE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIT_PRE_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_input_alignment as alignment_audit
from phase0_6_regression import EXTRA_TABLES, PublicSampleFeatureRepository
from pit_pre.features import (
    InputAlignmentDiagnostics,
    _align_series_with_trace,
    _feature_alignment_diagnostics,
    _max_raw_gap_seconds,
    _raw_timestamps,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/revision/phase0_6_1"),
    )
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def prepared_series(series: pd.DataFrame) -> pd.DataFrame:
    if series.empty:
        return series
    data = series.copy()
    data["measurement_time"] = pd.to_datetime(data["measurement_time"])
    return (
        data.sort_values(["measurement_time", "id"])
        .drop_duplicates("measurement_time", keep="last")
        [["measurement_time", "value"]]
        .dropna(subset=["value"])
    )


def value_only_alignment(
    series: pd.DataFrame,
    time_index: list[pd.Timestamp],
    tolerance: timedelta,
) -> list[float | None]:
    data = prepared_series(series)
    if data.empty:
        return [None for _ in time_index]
    target = pd.DataFrame({"time": pd.to_datetime(time_index)})
    aligned = pd.merge_asof(
        target,
        data.rename(columns={"measurement_time": "time"}).sort_values("time"),
        on="time",
        direction="backward",
        tolerance=pd.Timedelta(tolerance),
    )
    return [None if pd.isna(value) else float(value) for value in aligned["value"]]


def source_time_only_alignment(
    series: pd.DataFrame,
    time_index: list[pd.Timestamp],
    tolerance: timedelta,
) -> list[pd.Timestamp | None]:
    data = prepared_series(series)
    if data.empty:
        return [None for _ in time_index]
    data["source_time"] = data["measurement_time"]
    target = pd.DataFrame({"time": pd.to_datetime(time_index)})
    aligned = pd.merge_asof(
        target,
        data.rename(columns={"measurement_time": "time"}).sort_values("time"),
        on="time",
        direction="backward",
        tolerance=pd.Timedelta(tolerance),
    )
    return [None if pd.isna(value) else pd.Timestamp(value) for value in aligned["source_time"]]


def fixture() -> tuple[list[Any], dict[str, pd.DataFrame], list[pd.Timestamp], timedelta]:
    alignment_audit.AUDIT_TABLES.update(EXTRA_TABLES)
    tables = alignment_audit.parse_public_sample(
        ROOT / "sql/shm_em_database/02_SHM_EM_public_sample.sql"
    )
    models, features, project_id = alignment_audit.load_contract(
        ROOT, tables, alignment_audit.PROJECT_CODE
    )
    repository = PublicSampleFeatureRepository(tables, features, project_id)
    required_rows = max(int(model["required_history_rows"]) for model in models)
    latest_time = repository.find_latest_time(features)
    step = timedelta(minutes=int(models[0]["time_step_minutes"]))
    start_time = latest_time - step * (required_rows - 1)
    time_index = [pd.Timestamp(start_time + step * index) for index in range(required_rows)]
    series = {
        mapping.training_feature_code: repository.read_feature_series(
            mapping, start_time - step, latest_time
        )
        for mapping in features
    }
    return features, series, time_index, step


def build(
    mode: str,
    mappings: list[Any],
    series_by_code: dict[str, pd.DataFrame],
    time_index: list[pd.Timestamp],
    step: timedelta,
) -> tuple[pd.DataFrame, dict[str, Any] | None]:
    values: dict[str, list[float | None]] = {}
    source_times: dict[str, list[pd.Timestamp | None]] = {}
    for mapping in mappings:
        code = mapping.training_feature_code
        series = series_by_code[code]
        if mode == "phase0_6_1_one_pass":
            trace = _align_series_with_trace(series, time_index, step)
            values[code] = trace.values
            source_times[code] = trace.source_times
        else:
            values[code] = value_only_alignment(series, time_index, step)
            if mode == "phase0_6_two_pass":
                source_times[code] = source_time_only_alignment(series, time_index, step)

    initial = pd.DataFrame(values)
    interpolated = initial.interpolate(method="linear", limit_direction="both")
    forward = interpolated.ffill()
    filled = forward.bfill()
    summary = None
    if mode != "value_only":
        diagnostics = {
            code: _feature_alignment_diagnostics(
                time_index=time_index,
                initial=initial[code],
                interpolated=interpolated[code],
                forward_filled=forward[code],
                filled=filled[code],
                source_times=source_times[code],
                max_raw_gap_seconds=_max_raw_gap_seconds(series_by_code[code]),
                raw_timestamps=_raw_timestamps(series_by_code[code]),
            )
            for code in filled.columns
        }
        summary = InputAlignmentDiagnostics(
            time_step_seconds=int(step.total_seconds()),
            features=diagnostics,
            time_index=tuple(time_index),
        ).quality_summary(list(filled.columns), len(time_index))
    return filled, summary


def percentile(values: list[float], quantile: float) -> float:
    return float(pd.Series(values, dtype="float64").quantile(quantile))


def benchmark(repeats: int) -> dict[str, Any]:
    mappings, series, time_index, step = fixture()
    modes = ["value_only", "phase0_6_two_pass", "phase0_6_1_one_pass"]
    outputs = {mode: build(mode, mappings, series, time_index, step) for mode in modes}
    reference = outputs["value_only"][0].to_numpy(dtype=np.float64)
    numerical_diffs = {
        mode: float(np.max(np.abs(reference - outputs[mode][0].to_numpy(dtype=np.float64))))
        for mode in modes
    }
    timings: dict[str, list[float]] = {mode: [] for mode in modes}
    for mode in modes:
        build(mode, mappings, series, time_index, step)
        for _ in range(repeats):
            gc.collect()
            started = time.perf_counter()
            build(mode, mappings, series, time_index, step)
            timings[mode].append((time.perf_counter() - started) * 1000)
    measurements = {
        mode: {
            "samples": repeats,
            "medianMilliseconds": round(statistics.median(values), 3),
            "p95Milliseconds": round(percentile(values, 0.95), 3),
            "minMilliseconds": round(min(values), 3),
            "maxMilliseconds": round(max(values), 3),
        }
        for mode, values in timings.items()
    }
    two_pass = outputs["phase0_6_two_pass"][1]
    one_pass = outputs["phase0_6_1_one_pass"][1]
    stage_keys = [
        "exactCellCount",
        "asofCellCount",
        "interiorInterpolationCellCount",
        "leadingBoundaryExtensionCellCount",
        "trailingBoundaryExtensionCellCount",
        "forwardFillCellCount",
        "backwardFillCellCount",
        "unresolvedMissingCellCount",
    ]
    return {
        "schemaVersion": "shm-em-phase0-6-1-alignment-benchmark-v1",
        "scope": "public sample common 16-step wide-table build",
        "featureCount": len(mappings),
        "measurements": measurements,
        "maxNumericalAbsDifferenceByMode": numerical_diffs,
        "stageCountsIdentical": all(two_pass[key] == one_pass[key] for key in stage_keys),
        "twoPassStageCounts": {key: two_pass[key] for key in stage_keys},
        "onePassStageCounts": {key: one_pass[key] for key in stage_keys},
        "eligibilityThresholdsApplied": False,
    }


def render(report: dict[str, Any]) -> str:
    rows = [
        f"| {mode} | {item['medianMilliseconds']} | {item['p95Milliseconds']} | {item['minMilliseconds']} | {item['maxMilliseconds']} |"
        for mode, item in report["measurements"].items()
    ]
    return "\n".join([
        "# Phase 0.6.1 Alignment Diagnostics Overhead Benchmark",
        "",
        f"Scope: {report['scope']} with `{report['featureCount']}` mapped features.",
        "",
        "| Mode | Median (ms) | P95 (ms) | Min (ms) | Max (ms) |",
        "| --- | --- | --- | --- | --- |",
        *rows,
        "",
        f"- Maximum numerical difference across modes: `{max(report['maxNumericalAbsDifferenceByMode'].values())}`",
        f"- Two-pass and one-pass stage counts identical: `{str(report['stageCountsIdentical']).lower()}`",
        "- This is a local engineering microbenchmark, not a paper-level scalability claim.",
        "",
    ])


def main() -> int:
    args = parse_args()
    if args.repeats < 3:
        raise ValueError("--repeats must be at least 3")
    output_dir = resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = benchmark(args.repeats)
    (output_dir / "diagnostics-overhead-benchmark.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "diagnostics-overhead-benchmark.md").write_text(
        render(report),
        encoding="utf-8",
    )
    passed = (
        max(report["maxNumericalAbsDifferenceByMode"].values()) == 0.0
        and report["stageCountsIdentical"]
    )
    print(json.dumps({
        "measurements": report["measurements"],
        "passed": passed,
    }, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
