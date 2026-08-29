from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from pit_pre.config import ModelConfig
from pit_pre.features import (
    ALIGNMENT_POLICY_VERSION,
    FeatureAlignmentDiagnostics,
    InputAlignmentDiagnostics,
    WideTableBuilder,
    _align_series,
    _feature_alignment_diagnostics,
)
from pit_pre.result_writer import _input_snapshot


@dataclass(frozen=True)
class Mapping:
    training_feature_code: str


class FakeRepository:
    def __init__(self, series: pd.DataFrame):
        self.mapping = Mapping("feature_a")
        self.series = series

    def load_enabled_mappings(self):
        return [self.mapping]

    def find_latest_time(self, mappings):
        return pd.Timestamp(self.series["measurement_time"].max()).to_pydatetime()

    def read_feature_series(self, mapping, start_time, end_time):
        return self.series[
            (self.series["measurement_time"] >= pd.Timestamp(start_time))
            & (self.series["measurement_time"] <= pd.Timestamp(end_time))
        ].copy()


class AlignmentDiagnosticsTest(unittest.TestCase):
    def test_alignment_diagnostics_do_not_change_values(self) -> None:
        start = pd.Timestamp("2026-01-01 00:00:00")
        series = pd.DataFrame({
            "measurement_time": [start, start + timedelta(minutes=3), start + timedelta(minutes=9)],
            "value": [1.0, 2.0, 4.0],
            "id": [1, 2, 3],
        })
        builder = WideTableBuilder(FakeRepository(series), 3)
        result = builder.build_with_diagnostics(4)

        time_index = [start + timedelta(minutes=3 * index) for index in range(4)]
        reference_values = _align_series(series, time_index, timedelta(minutes=3))
        reference = pd.DataFrame({
            "time": time_index,
            "time1": range(1, 5),
            "feature_a": reference_values,
        })
        reference[["feature_a"]] = (
            reference[["feature_a"]]
            .interpolate(method="linear", limit_direction="both")
            .ffill()
            .bfill()
        )
        assert_frame_equal(reference, result.values)

    def test_builder_uses_one_asof_merge_per_feature(self) -> None:
        start = pd.Timestamp("2026-01-01 00:00:00")
        series = pd.DataFrame({
            "measurement_time": [start, start + timedelta(minutes=3)],
            "value": [1.0, 2.0],
            "id": [1, 2],
        })
        original_merge_asof = pd.merge_asof
        with patch("pit_pre.features.pd.merge_asof", wraps=original_merge_asof) as merge_asof:
            WideTableBuilder(FakeRepository(series), 3).build_with_diagnostics(2)
        self.assertEqual(1, merge_asof.call_count)

    def test_alignment_stage_attribution(self) -> None:
        start = datetime(2026, 1, 1)
        times = [start + timedelta(minutes=3 * index) for index in range(3)]
        initial = pd.Series([1.0, None, 3.0], dtype="float64")
        interpolated = initial.interpolate(method="linear", limit_direction="both")
        diagnostics = _feature_alignment_diagnostics(
            time_index=times,
            initial=initial,
            interpolated=interpolated,
            forward_filled=interpolated.ffill(),
            filled=interpolated.ffill().bfill(),
            source_times=[pd.Timestamp(start - timedelta(seconds=20)), None, pd.Timestamp(times[2])],
            max_raw_gap_seconds=360.0,
        )
        self.assertEqual(
            ("backward_asof", "interior_interpolation", "exact_timestamp_match"),
            diagnostics.stages,
        )
        self.assertEqual(((20.0,), (200.0, -180.0), (0.0,)), diagnostics.source_offsets_seconds)

    def test_boundary_extension_attribution(self) -> None:
        start = datetime(2026, 1, 1)
        times = [start + timedelta(minutes=3 * index) for index in range(3)]
        initial = pd.Series([None, 2.0, None], dtype="float64")
        interpolated = initial.interpolate(method="linear", limit_direction="both")
        diagnostics = _feature_alignment_diagnostics(
            time_index=times,
            initial=initial,
            interpolated=interpolated,
            forward_filled=interpolated.ffill(),
            filled=interpolated.ffill().bfill(),
            source_times=[None, pd.Timestamp(times[1]), None],
            max_raw_gap_seconds=None,
        )
        self.assertEqual(
            (
                "leading_boundary_extension",
                "exact_timestamp_match",
                "trailing_boundary_extension",
            ),
            diagnostics.stages,
        )
        self.assertEqual(((-180.0,), (0.0,), (180.0,)), diagnostics.source_offsets_seconds)

    def test_quality_summary_counts_match_cells(self) -> None:
        diagnostics = InputAlignmentDiagnostics(
            time_step_seconds=180,
            features={
                "a": FeatureAlignmentDiagnostics(
                    stages=("exact_timestamp_match", "backward_asof", "interior_interpolation"),
                    source_offsets_seconds=((0.0,), (20.0,), (180.0, -180.0)),
                    max_raw_gap_seconds=360.0,
                ),
                "b": FeatureAlignmentDiagnostics(
                    stages=("leading_boundary_extension", "trailing_boundary_extension", "backward_fill"),
                    source_offsets_seconds=((-180.0,), (180.0,), (-360.0,)),
                    max_raw_gap_seconds=540.0,
                ),
            },
        )
        summary = diagnostics.quality_summary(["a", "b"], 3)
        counted = sum(summary[key] for key in (
            "exactCellCount",
            "asofCellCount",
            "interiorInterpolationCellCount",
            "leadingBoundaryExtensionCellCount",
            "trailingBoundaryExtensionCellCount",
            "forwardFillCellCount",
            "backwardFillCellCount",
            "unresolvedMissingCellCount",
        ))
        self.assertEqual(summary["inputCellCount"], counted)
        self.assertAlmostEqual(4 / 6, summary["fillRatio"])
        self.assertAlmostEqual(5 / 6, summary["nonExactAlignmentRatio"])
        self.assertEqual(540.0, summary["maxRawGapSeconds"])
        self.assertEqual(3, summary["pastSourceCellCount"])
        self.assertEqual(3, summary["futureSourceCellCount"])
        self.assertEqual(3, summary["pastSourceContributorCount"])
        self.assertEqual(3, summary["futureSourceContributorCount"])
        self.assertEqual(180.0, summary["maxPastSourceLagSeconds"])
        self.assertEqual(360.0, summary["maxFutureSourceLeadSeconds"])

    @patch("pit_pre.result_writer._runtime_environment", return_value={"python": "test"})
    def test_alignment_policy_metadata_is_persisted(self, _runtime) -> None:
        model = ModelConfig(
            id=1,
            code="test",
            target_type="test",
            script_path=Path("predict.py"),
            model_path=Path("model.pth"),
            preprocessor_path=Path("preprocessor.joblib"),
            runtime_manifest_path=Path("runtime-manifest.json"),
            required_history_rows=3,
            model_version="v1",
            artifact_hash="a",
            preprocessor_hash="b",
            inference_script_hash="c",
            best_params_hash=None,
            runtime_manifest_hash="d",
            environment_digest="e",
            artifact_bundle_hash="f",
            input_schema_hash="g",
            contract_version="v1",
            expected_steps=40,
            time_step_minutes=3,
            max_operational_age_minutes=15,
        )
        metadata = {
            "alignmentPolicyVersion": ALIGNMENT_POLICY_VERSION,
            "timeStepSeconds": 180,
            "asofToleranceSeconds": 180,
            "alignmentMethod": ["backward_asof"],
            "qualitySummary": {"inputCellCount": 3, "fillRatio": 0.0},
        }
        snapshot = _input_snapshot(model, "RUN-1", "pit_pre_v1", metadata)
        self.assertEqual(ALIGNMENT_POLICY_VERSION, snapshot["alignmentPolicyVersion"])
        self.assertEqual(metadata["qualitySummary"], snapshot["qualitySummary"])
        self.assertNotIn("maxFillRatioAllowed", snapshot)
        self.assertNotIn("eligible", snapshot)


if __name__ == "__main__":
    unittest.main()
