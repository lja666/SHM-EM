from __future__ import annotations

import argparse
from pathlib import Path

from pit_pre.cached_model_runner import CachedModelRunner
from pit_pre.config import load_config
from pit_pre.contract import load_app_config
from pit_pre.pipeline import PredictionPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PIT_PRE prediction pipeline.")
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to PIT_PRE config JSON. Defaults to ./config.json.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Optional model subset. By default all active database contracts are run.",
    )
    parser.add_argument("--project-code", default="SHM_EM_PUBLIC_SAMPLE")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_file():
        raise SystemExit(f"PIT_PRE configuration file not found: {config_path}")

    bootstrap = load_config(config_path)
    config = load_app_config(bootstrap, args.project_code)
    model_codes = args.models or list(config.models)
    unknown_models = [code for code in model_codes if code not in config.models]
    if unknown_models:
        raise SystemExit(f"Unknown model code(s): {', '.join(unknown_models)}")

    selected_models = {code: config.models[code] for code in model_codes}
    runner = CachedModelRunner(selected_models)
    pipeline = PredictionPipeline(config, model_runner=runner)

    print(
        "PIT_PRE run mode: "
        f"mode={config.runtime.prediction_mode}, "
        "effective_rolling=True, "
        f"horizon_minutes={config.runtime.prediction_horizon_minutes}"
    )
    summaries = pipeline.run_models(model_codes)
    for item in summaries:
        print(
            f"{item.model_code}: output_rows={item.output_rows}, "
            f"inserted_rows={item.inserted_rows}, "
            f"elapsed_seconds={item.elapsed_seconds:.2f}"
        )


if __name__ == "__main__":
    main()
