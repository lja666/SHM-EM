from __future__ import annotations

import argparse
import os
import time
from datetime import datetime
from pathlib import Path

from pit_pre.cached_model_runner import CachedModelRunner
from pit_pre.config import load_config
from pit_pre.contract import load_app_config
from pit_pre.pipeline import PredictionPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PIT_PRE as a persistent prediction daemon.")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--project-code", default="SHM_EM_PUBLIC_SAMPLE")
    parser.add_argument("--interval-seconds", type=int, default=180)
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_file():
        raise SystemExit(f"PIT_PRE configuration file not found: {config_path}")

    bootstrap = load_config(config_path)
    config = load_app_config(bootstrap, args.project_code)
    model_codes = args.models or list(config.models)
    pipeline = build_pipeline(config, model_codes)

    print(
        "PIT_PRE daemon started. "
        f"models={','.join(model_codes)}, interval={args.interval_seconds}s, "
        f"mode={config.runtime.prediction_mode}, "
        "effective_rolling=True, "
        f"horizon_minutes={config.runtime.prediction_horizon_minutes}"
    )
    while True:
        cleanup_logs_if_monday()
        started = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            current = load_app_config(bootstrap, args.project_code)
            if current.contract_fingerprint != config.contract_fingerprint:
                config = current
                model_codes = args.models or list(config.models)
                pipeline = build_pipeline(config, model_codes)
                print(f"{started} database model contract changed; prediction runtime reloaded.")
            summaries = pipeline.run_models(model_codes)
            for item in summaries:
                print(
                    f"{started} {item.model_code}: "
                    f"output_rows={item.output_rows}, inserted_rows={item.inserted_rows}, "
                    f"elapsed_seconds={item.elapsed_seconds:.2f}"
                )
        except Exception as exc:
            print(f"{started} PIT_PRE prediction cycle failed: {exc}", flush=True)
        time.sleep(args.interval_seconds)


def build_pipeline(config, model_codes: list[str]) -> PredictionPipeline:
    unknown_models = [code for code in model_codes if code not in config.models]
    if unknown_models:
        raise SystemExit(f"Unknown model code(s): {', '.join(unknown_models)}")
    selected_models = {code: config.models[code] for code in model_codes}
    runner = CachedModelRunner(selected_models)
    return PredictionPipeline(config, model_runner=runner)


def cleanup_logs_if_monday() -> None:
    now = datetime.now()
    if now.isoweekday() != 1:
        return

    log_paths = [
        os.environ.get("PIT_PRE_LOGFILE"),
        os.environ.get("PIT_PRE_SERVICE_LOGFILE"),
        os.environ.get("PIT_PRE_SERVICE_ERROR_LOGFILE"),
    ]
    log_paths = [Path(p) for p in log_paths if p]
    if not log_paths:
        return

    state_dir = log_paths[0].parent
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / ".pit_pre_last_log_cleanup_week"
    current_week = now.strftime("%G-W%V")

    if state_file.exists() and state_file.read_text(encoding="utf-8").strip() == current_week:
        return

    for path in log_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    state_file.write_text(current_week, encoding="utf-8")
    print(f"{now:%Y-%m-%d %H:%M:%S} PIT_PRE weekly log cleanup finished.")


if __name__ == "__main__":
    main()
