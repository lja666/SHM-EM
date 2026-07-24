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
        mappings = self.repository.load_enabled_mappings()
        latest_time = self.repository.find_latest_time(mappings)
        step = timedelta(minutes=self.time_step_minutes)
        start_time = latest_time - step * (required_rows - 1)
        time_index = [start_time + step * i for i in range(required_rows)]

        feature_data: dict[str, list[float | None]] = {}
        for mapping in mappings:
            series = self.repository.read_feature_series(mapping, start_time - step, latest_time)
            feature_data[mapping.training_feature_code] = _align_series(
                series,
                time_index,
                step,
            )

        wide = pd.concat(
            [
                pd.DataFrame({"time": time_index, "time1": range(1, required_rows + 1)}),
                pd.DataFrame(feature_data),
            ],
            axis=1,
        )
        feature_columns = [col for col in wide.columns if col not in {"time", "time1"}]
        wide[feature_columns] = (
            wide[feature_columns]
            .interpolate(method="linear", limit_direction="both")
            .ffill()
            .bfill()
        )

        missing = wide[feature_columns].isna().sum()
        missing = missing[missing > 0]
        if not missing.empty:
            raise ValueError(f"Prediction input window has missing feature values:\n{missing}")

        return wide


def _align_series(
    series: pd.DataFrame,
    time_index: list[datetime],
    tolerance: timedelta,
) -> list[float | None]:
    if series.empty:
        return [None for _ in time_index]

    data = series.copy()
    data["measurement_time"] = pd.to_datetime(data["measurement_time"])
    # If a sensor has multiple rows in one timestamp, keep the newest id.
    data = data.sort_values(["measurement_time", "id"]).drop_duplicates("measurement_time", keep="last")
    data = data[["measurement_time", "value"]].dropna(subset=["value"])
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
    return [
        None if pd.isna(value) else float(value)
        for value in aligned["value"].tolist()
    ]
