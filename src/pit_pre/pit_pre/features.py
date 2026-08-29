from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from pit_pre.db import Database


ALLOWED_VALUE_COLUMNS = {
    "raw_value",
    "metric_value",
    "baseline_value",
}

ALLOWED_OBSERVATION_TABLES = {
    "em_obs_displacement",
    "em_obs_earth_pressure",
    "em_obs_pressure_water_level",
    "em_obs_static_level",
}

ALIGNMENT_POLICY_VERSION = "pit_pre_alignment_v2"
ALIGNMENT_METHOD = (
    "backward_asof",
    "interior_linear_interpolation",
    "boundary_extension",
    "ffill",
    "bfill",
)


@dataclass(frozen=True)
class FeatureMapping:
    id: int
    project_id: int
    feature_code: str
    feature_name: str
    training_feature_code: str
    feature_group: str
    target_type: str
    station_id: int | None
    instrument_id: int | None
    source_metric_code: str
    source_registry_code: str
    source_table_name: str
    source_value_column: str
    source_field: str
    feature_order: int
    metric_unit: str | None


@dataclass(frozen=True)
class FeatureAlignmentDiagnostics:
    stages: tuple[str, ...]
    source_offsets_seconds: tuple[tuple[float, ...], ...]
    max_raw_gap_seconds: float | None
    raw_timestamps: tuple[pd.Timestamp, ...] = ()


@dataclass(frozen=True)
class InputAlignmentDiagnostics:
    time_step_seconds: int
    features: dict[str, FeatureAlignmentDiagnostics]
    time_index: tuple[pd.Timestamp, ...] = ()

    def quality_summary(
        self,
        feature_codes: list[str],
        history_window_size: int,
    ) -> dict[str, int | float | None]:
        traces = [self.features[code] for code in feature_codes]
        stages = [
            stage
            for trace in traces
            for stage in trace.stages[-history_window_size:]
        ]
        offset_groups = [
            offsets
            for trace in traces
            for offsets in trace.source_offsets_seconds[-history_window_size:]
        ]
        source_offsets = [offset for offsets in offset_groups for offset in offsets]
        absolute_offsets = [abs(offset) for offset in source_offsets]
        past_offsets = [offset for offset in source_offsets if offset > 0]
        future_offsets = [-offset for offset in source_offsets if offset < 0]
        counts = pd.Series(stages, dtype="object").value_counts().to_dict()
        input_cells = history_window_size * len(feature_codes)
        interior = int(counts.get("interior_interpolation", 0))
        leading = int(counts.get("leading_boundary_extension", 0))
        trailing = int(counts.get("trailing_boundary_extension", 0))
        forward = int(counts.get("forward_fill", 0))
        backward = int(counts.get("backward_fill", 0))
        asof = int(counts.get("backward_asof", 0))
        fill_cells = interior + leading + trailing + forward + backward
        non_exact_cells = asof + fill_cells
        raw_gaps: list[float] = []
        if self.time_index:
            window_start = self.time_index[-history_window_size] - pd.Timedelta(
                seconds=self.time_step_seconds
            )
            window_end = self.time_index[-1]
            for trace in traces:
                timestamps = [
                    timestamp
                    for timestamp in trace.raw_timestamps
                    if window_start <= timestamp <= window_end
                ]
                gap = _max_timestamp_gap_seconds(timestamps)
                if gap is not None:
                    raw_gaps.append(gap)
        else:
            raw_gaps = [
                trace.max_raw_gap_seconds
                for trace in traces
                if trace.max_raw_gap_seconds is not None
            ]
        return {
            "inputCellCount": input_cells,
            "exactCellCount": int(counts.get("exact_timestamp_match", 0)),
            "asofCellCount": asof,
            "interiorInterpolationCellCount": interior,
            "leadingBoundaryExtensionCellCount": leading,
            "trailingBoundaryExtensionCellCount": trailing,
            "boundaryExtensionCellCount": leading + trailing,
            "forwardFillCellCount": forward,
            "backwardFillCellCount": backward,
            "unresolvedMissingCellCount": int(counts.get("missing", 0)),
            "fillRatio": _ratio(fill_cells, input_cells),
            "nonExactAlignmentRatio": _ratio(non_exact_cells, input_cells),
            "medianAbsoluteSourceOffsetSeconds": _quantile(absolute_offsets, 0.5),
            "p95AbsoluteSourceOffsetSeconds": _quantile(absolute_offsets, 0.95),
            "maxAbsoluteSourceOffsetSeconds": max(absolute_offsets) if absolute_offsets else None,
            "pastSourceCellCount": sum(any(offset > 0 for offset in offsets) for offsets in offset_groups),
            "futureSourceCellCount": sum(any(offset < 0 for offset in offsets) for offsets in offset_groups),
            "pastSourceContributorCount": len(past_offsets),
            "futureSourceContributorCount": len(future_offsets),
            "maxPastSourceLagSeconds": max(past_offsets) if past_offsets else None,
            "maxFutureSourceLeadSeconds": max(future_offsets) if future_offsets else None,
            "maxRawGapSeconds": max(raw_gaps) if raw_gaps else None,
        }

    def snapshot_metadata(
        self,
        feature_codes: list[str],
        history_window_size: int,
    ) -> dict[str, Any]:
        return {
            "alignmentPolicyVersion": ALIGNMENT_POLICY_VERSION,
            "timeStepSeconds": self.time_step_seconds,
            "asofToleranceSeconds": self.time_step_seconds,
            "alignmentMethod": list(ALIGNMENT_METHOD),
            "qualitySummary": self.quality_summary(feature_codes, history_window_size),
        }


@dataclass(frozen=True)
class AlignedInput:
    values: pd.DataFrame
    diagnostics: InputAlignmentDiagnostics


@dataclass(frozen=True)
class AlignmentTrace:
    values: list[float | None]
    source_times: list[pd.Timestamp | None]


def validate_identifier(value: str, allowed: set[str], kind: str) -> str:
    value = value.strip()
    if value not in allowed:
        raise ValueError(f"Unsupported {kind}: {value}")
    return value


class FeatureRepository:
    def __init__(self, db: Database, project_code: str, schema_version: str = "pit_pre_v1"):
        self.db = db
        self.project_code = project_code
        self.schema_version = schema_version
        self._project_id: int | None = None

    @property
    def project_id(self) -> int:
        if self._project_id is None:
            df = self.db.read_frame(
                """
                SELECT id
                FROM em_project
                WHERE project_code = %s
                LIMIT 1
                """,
                [self.project_code],
            )
            if df.empty:
                raise ValueError(f"Cannot find SHM-EM project_code={self.project_code}")
            self._project_id = int(df.iloc[0]["id"])
        return self._project_id

    def load_enabled_mappings(self) -> list[FeatureMapping]:
        sql = """
            SELECT
                f.id,
                f.project_id,
                f.feature_code,
                COALESCE(f.feature_name, f.feature_code) AS feature_name,
                COALESCE(
                    NULLIF(f.training_feature_code, ''),
                    JSON_UNQUOTE(JSON_EXTRACT(f.metadata_json, '$.trainingFeatureCode')),
                    f.feature_code
                ) AS training_feature_code,
                COALESCE(f.feature_group, f.target_type) AS feature_group,
                COALESCE(f.target_type, f.feature_group) AS target_type,
                f.station_id,
                f.instrument_id,
                f.source_metric_code,
                f.source_registry_code,
                r.physical_table_name AS source_table_name,
                COALESCE(NULLIF(f.source_value_column, ''), NULLIF(f.source_field, ''), 'metric_value') AS source_value_column,
                COALESCE(NULLIF(f.source_field, ''), NULLIF(f.source_value_column, ''), 'metric_value') AS source_field,
                f.feature_order,
                m.default_unit AS metric_unit
            FROM em_prediction_feature_mapping f
            INNER JOIN em_observation_table_registry r
                    ON r.registry_code = f.source_registry_code
                   AND r.project_id = f.project_id
                   AND r.enabled = 1
                   AND r.is_queryable = 1
            LEFT JOIN em_metric m ON m.metric_code = f.source_metric_code
            WHERE f.project_id = %s
              AND f.schema_version = %s
              AND f.enabled = 1
              AND COALESCE(f.feature_role, 'model_input') = 'model_input'
            ORDER BY f.feature_order ASC, f.id ASC
        """
        df = self.db.read_frame(sql, [self.project_id, self.schema_version])
        mappings: list[FeatureMapping] = []
        for row in df.to_dict("records"):
            source_value_column = validate_identifier(
                str(row["source_value_column"]),
                ALLOWED_VALUE_COLUMNS,
                "observation value column",
            )
            source_metric_code = str(row.get("source_metric_code") or "").strip()
            if not source_metric_code:
                raise ValueError(f"Feature {row['feature_code']} must configure source_metric_code")
            station_id = _nullable_int(row.get("station_id"))
            instrument_id = _nullable_int(row.get("instrument_id"))
            if station_id is None and instrument_id is None:
                raise ValueError(f"Feature {row['feature_code']} must configure station_id or instrument_id")
            source_registry_code = str(row.get("source_registry_code") or "").strip()
            if not source_registry_code:
                raise ValueError(f"Feature {row['feature_code']} must configure source_registry_code")
            source_table_name = validate_identifier(
                str(row.get("source_table_name") or ""),
                ALLOWED_OBSERVATION_TABLES,
                "observation table",
            )
            mappings.append(
                FeatureMapping(
                    id=int(row["id"]),
                    project_id=int(row["project_id"]),
                    feature_code=str(row["feature_code"]).strip(),
                    feature_name=str(row["feature_name"]).strip(),
                    training_feature_code=str(row["training_feature_code"]).strip(),
                    feature_group=str(row["feature_group"]).strip(),
                    target_type=str(row["target_type"]).strip(),
                    station_id=station_id,
                    instrument_id=instrument_id,
                    source_metric_code=source_metric_code,
                    source_registry_code=source_registry_code,
                    source_table_name=source_table_name,
                    source_value_column=source_value_column,
                    source_field=str(row["source_field"]).strip(),
                    feature_order=int(row["feature_order"]),
                    metric_unit=None if pd.isna(row.get("metric_unit")) else str(row.get("metric_unit")),
                )
            )
        if not mappings:
            raise ValueError(
                "No enabled SHM-EM prediction feature mappings for "
                f"project_code={self.project_code}, schema_version={self.schema_version}."
            )
        return mappings

    def find_latest_time(self, mappings: list[FeatureMapping]) -> datetime:
        latest_times: list[pd.Timestamp] = []
        for mapping in mappings:
            clauses, params = _identity_where(mapping)
            sql = f"""
                SELECT MAX(observed_at) AS latest_time
                FROM {mapping.source_table_name}
                WHERE project_id = %s
                  AND metric_code = %s
                  AND {mapping.source_value_column} IS NOT NULL
                  {clauses}
            """
            df = self.db.read_frame(sql, [mapping.project_id, mapping.source_metric_code, *params])
            value = df.iloc[0]["latest_time"] if not df.empty else None
            if pd.notna(value):
                latest_times.append(pd.Timestamp(value))
        if not latest_times:
            raise ValueError("Cannot find latest observed_at from configured SHM-EM prediction features")

        # Use the minimum latest time so every configured source can contribute
        # to the same model input window.
        return min(latest_times).to_pydatetime()

    def read_feature_series(
        self,
        mapping: FeatureMapping,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        clauses, params = _identity_where(mapping)
        sql = f"""
            SELECT observed_at AS measurement_time,
                   {mapping.source_value_column} AS value,
                   id,
                   created_at
            FROM {mapping.source_table_name}
            WHERE project_id = %s
              AND metric_code = %s
              AND observed_at >= %s
              AND observed_at <= %s
              AND {mapping.source_value_column} IS NOT NULL
              {clauses}
            ORDER BY observed_at ASC, id ASC
        """
        return self.db.read_frame(sql, [mapping.project_id, mapping.source_metric_code, start_time, end_time, *params])


def _identity_where(mapping: FeatureMapping) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if mapping.station_id is not None:
        clauses.append("AND station_id = %s")
        params.append(mapping.station_id)
    if mapping.instrument_id is not None:
        clauses.append("AND instrument_id = %s")
        params.append(mapping.instrument_id)
    return "\n                  ".join(clauses), params


def _nullable_int(value) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)


class WideTableBuilder:
    def __init__(self, repository: FeatureRepository, time_step_minutes: int):
        self.repository = repository
        self.time_step_minutes = time_step_minutes

    def build(self, required_rows: int) -> pd.DataFrame:
        return self.build_with_diagnostics(required_rows).values

    def build_with_diagnostics(self, required_rows: int) -> AlignedInput:
        mappings = self.repository.load_enabled_mappings()
        latest_time = self.repository.find_latest_time(mappings)
        step = timedelta(minutes=self.time_step_minutes)
        start_time = latest_time - step * (required_rows - 1)
        time_index = [start_time + step * i for i in range(required_rows)]

        feature_data: dict[str, list[float | None]] = {}
        source_times: dict[str, list[pd.Timestamp | None]] = {}
        raw_gaps: dict[str, float | None] = {}
        raw_timestamps: dict[str, tuple[pd.Timestamp, ...]] = {}
        for mapping in mappings:
            series = self.repository.read_feature_series(mapping, start_time - step, latest_time)
            trace = _align_series_with_trace(
                series,
                time_index,
                step,
            )
            feature_data[mapping.training_feature_code] = trace.values
            source_times[mapping.training_feature_code] = trace.source_times
            raw_gaps[mapping.training_feature_code] = _max_raw_gap_seconds(series)
            raw_timestamps[mapping.training_feature_code] = _raw_timestamps(series)

        wide = pd.concat(
            [
                pd.DataFrame({"time": time_index, "time1": range(1, required_rows + 1)}),
                pd.DataFrame(feature_data),
            ],
            axis=1,
        )
        feature_columns = [col for col in wide.columns if col not in {"time", "time1"}]
        initial = wide[feature_columns].copy()
        interpolated = initial.interpolate(method="linear", limit_direction="both")
        forward_filled = interpolated.ffill()
        filled = forward_filled.bfill()
        wide[feature_columns] = filled

        missing = wide[feature_columns].isna().sum()
        missing = missing[missing > 0]
        if not missing.empty:
            raise ValueError(f"Prediction input window has missing feature values:\n{missing}")

        diagnostics = {
            code: _feature_alignment_diagnostics(
                time_index=time_index,
                initial=initial[code],
                interpolated=interpolated[code],
                forward_filled=forward_filled[code],
                filled=filled[code],
                source_times=source_times[code],
                max_raw_gap_seconds=raw_gaps[code],
                raw_timestamps=raw_timestamps[code],
            )
            for code in feature_columns
        }
        return AlignedInput(
            values=wide,
            diagnostics=InputAlignmentDiagnostics(
                time_step_seconds=int(step.total_seconds()),
                features=diagnostics,
                time_index=tuple(pd.Timestamp(value) for value in time_index),
            ),
        )


def _align_series(
    series: pd.DataFrame,
    time_index: list[datetime],
    tolerance: timedelta,
) -> list[float | None]:
    return _align_series_with_trace(series, time_index, tolerance).values


def _align_series_with_trace(
    series: pd.DataFrame,
    time_index: list[datetime],
    tolerance: timedelta,
) -> AlignmentTrace:
    if series.empty:
        empty = [None for _ in time_index]
        return AlignmentTrace(values=empty, source_times=empty.copy())

    data = series.copy()
    data["measurement_time"] = pd.to_datetime(data["measurement_time"])
    # If a sensor has multiple rows in one timestamp, keep the newest id.
    data = data.sort_values(["measurement_time", "id"]).drop_duplicates("measurement_time", keep="last")
    data = data[["measurement_time", "value"]].dropna(subset=["value"])
    if data.empty:
        empty = [None for _ in time_index]
        return AlignmentTrace(values=empty, source_times=empty.copy())

    data["source_time"] = data["measurement_time"]
    target = pd.DataFrame({"time": pd.to_datetime(time_index)})
    aligned = pd.merge_asof(
        target,
        data.rename(columns={"measurement_time": "time"}).sort_values("time"),
        on="time",
        direction="backward",
        tolerance=pd.Timedelta(tolerance),
    )
    values = [
        None if pd.isna(value) else float(value)
        for value in aligned["value"].tolist()
    ]
    source_times = [
        None if pd.isna(value) else pd.Timestamp(value)
        for value in aligned["source_time"].tolist()
    ]
    return AlignmentTrace(values=values, source_times=source_times)


def _max_raw_gap_seconds(series: pd.DataFrame) -> float | None:
    return _max_timestamp_gap_seconds(_raw_timestamps(series))


def _raw_timestamps(series: pd.DataFrame) -> tuple[pd.Timestamp, ...]:
    if series.empty:
        return tuple()
    data = series.copy()
    data["measurement_time"] = pd.to_datetime(data["measurement_time"])
    timestamps = tuple(
        data.sort_values(["measurement_time", "id"])
        .drop_duplicates("measurement_time", keep="last")
        .dropna(subset=["value"])["measurement_time"]
        .sort_values()
        .map(pd.Timestamp)
        .tolist()
    )
    return timestamps


def _max_timestamp_gap_seconds(
    timestamps: list[pd.Timestamp] | tuple[pd.Timestamp, ...],
) -> float | None:
    if len(timestamps) < 2:
        return None
    return max(
        float((current - previous).total_seconds())
        for previous, current in zip(timestamps, timestamps[1:])
    )


def _feature_alignment_diagnostics(
    time_index: list[datetime],
    initial: pd.Series,
    interpolated: pd.Series,
    forward_filled: pd.Series,
    filled: pd.Series,
    source_times: list[pd.Timestamp | None],
    max_raw_gap_seconds: float | None,
    raw_timestamps: tuple[pd.Timestamp, ...] = (),
) -> FeatureAlignmentDiagnostics:
    stages: list[str] = []
    lineage: list[tuple[pd.Timestamp, ...]] = []
    for target_time, value, source_time in zip(time_index, initial, source_times):
        if pd.isna(value) or source_time is None:
            stages.append("missing")
            lineage.append(tuple())
        elif pd.Timestamp(target_time) == source_time:
            stages.append("exact_timestamp_match")
            lineage.append((source_time,))
        else:
            stages.append("backward_asof")
            lineage.append((source_time,))

    populated = [index for index, value in enumerate(initial) if pd.notna(value)]
    for index, (before, after) in enumerate(zip(initial, interpolated)):
        if pd.notna(before) or pd.isna(after):
            continue
        previous = [position for position in populated if position < index]
        following = [position for position in populated if position > index]
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
        lineage[index] = tuple(dict.fromkeys(contributors))

    for index, (before, after) in enumerate(zip(interpolated, forward_filled)):
        if pd.notna(before) or pd.isna(after):
            continue
        previous = next(
            (
                position
                for position in range(index - 1, -1, -1)
                if pd.notna(forward_filled.iloc[position])
            ),
            None,
        )
        stages[index] = "forward_fill"
        lineage[index] = tuple() if previous is None else lineage[previous]

    for index, (before, after) in enumerate(zip(forward_filled, filled)):
        if pd.notna(before) or pd.isna(after):
            continue
        following = next(
            (
                position
                for position in range(index + 1, len(filled))
                if pd.notna(filled.iloc[position])
            ),
            None,
        )
        stages[index] = "backward_fill"
        lineage[index] = tuple() if following is None else lineage[following]

    offsets: list[tuple[float, ...]] = []
    for target_time, value, sources in zip(time_index, filled, lineage):
        if pd.isna(value):
            stages[len(offsets)] = "missing"
            offsets.append(tuple())
        elif not sources:
            offsets.append(tuple())
        else:
            offsets.append(tuple(
                float((pd.Timestamp(target_time) - source).total_seconds())
                for source in sources
            ))
    return FeatureAlignmentDiagnostics(
        stages=tuple(stages),
        source_offsets_seconds=tuple(offsets),
        max_raw_gap_seconds=max_raw_gap_seconds,
        raw_timestamps=raw_timestamps,
    )


def _ratio(count: int, total: int) -> float:
    return round(count / total, 12) if total else 0.0


def _quantile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    return round(float(pd.Series(values, dtype="float64").quantile(quantile)), 6)
