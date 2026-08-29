#!/usr/bin/env python3
"""Validate public PIT_PRE contracts against raw checkout bytes.

The validator deliberately performs no line-ending normalization. It also
creates a minimal Git repository and clones it with ``core.autocrlf=true`` to
verify that the declared byte hashes survive a normal Windows checkout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PIT_PRE_ROOT = ROOT / "src/pit_pre"
if str(PIT_PRE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIT_PRE_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_input_alignment as alignment_audit
from phase0_6_regression import EXTRA_TABLES, model_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/revision/phase0_6_1"),
    )
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def attributes(path: str) -> dict[str, str]:
    output = git("check-attr", "text", "eol", "--", path)
    result: dict[str, str] = {}
    for line in output.splitlines():
        _, attribute, value = line.rsplit(": ", 2)
        result[attribute] = value
    return result


def eol_state(path: str) -> str:
    return git("ls-files", "--eol", "--", path)


def text_eol_counts(path: Path) -> dict[str, int]:
    content = path.read_bytes()
    return {
        "crlfCount": content.count(b"\r\n"),
        "bareCarriageReturnCount": content.replace(b"\r\n", b"").count(b"\r"),
        "lfCount": content.count(b"\n") - content.count(b"\r\n"),
    }


def contract_assets() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    alignment_audit.AUDIT_TABLES.update(EXTRA_TABLES)
    tables = alignment_audit.parse_public_sample(
        ROOT / "sql/shm_em_database/02_SHM_EM_public_sample.sql"
    )
    config = model_config(tables, alignment_audit.PROJECT_CODE)
    models: list[dict[str, Any]] = []
    assets: dict[str, dict[str, Any]] = {}

    def add_asset(path: Path, kind: str, declared_hash: str | None) -> None:
        key = relative(path)
        item = assets.setdefault(key, {
            "path": key,
            "kinds": [],
            "declaredHashes": [],
            "textArtifact": kind in {"inference_script", "best_params", "runtime_manifest", "dependency_lock"},
        })
        if kind not in item["kinds"]:
            item["kinds"].append(kind)
        if declared_hash and declared_hash not in item["declaredHashes"]:
            item["declaredHashes"].append(declared_hash)

    for model in config.models.values():
        runtime_manifest = json.loads(model.runtime_manifest_path.read_text(encoding="utf-8"))
        dependency_lock_path = PIT_PRE_ROOT / str(runtime_manifest["dependencyLock"]).removeprefix("./")
        add_asset(model.model_path, "model_artifact", model.artifact_hash)
        add_asset(model.preprocessor_path, "preprocessor", model.preprocessor_hash)
        add_asset(model.script_path, "inference_script", model.inference_script_hash)
        if model.best_params_path:
            add_asset(model.best_params_path, "best_params", model.best_params_hash)
        add_asset(model.runtime_manifest_path, "runtime_manifest", model.runtime_manifest_hash)
        add_asset(dependency_lock_path, "dependency_lock", None)
        lock_hash = sha256_file(dependency_lock_path)
        calculated_environment = sha256_text(f"{lock_hash}|{model.runtime_manifest_hash}")
        calculated_bundle = sha256_text("|".join([
            model.artifact_hash,
            model.preprocessor_hash,
            model.inference_script_hash,
            model.best_params_hash or "",
            model.input_schema_hash,
            model.contract_version,
            model.runtime_manifest_hash,
            model.environment_digest,
        ]))
        models.append({
            "modelCode": model.code,
            "environmentDigestDeclared": model.environment_digest,
            "environmentDigestCalculated": calculated_environment,
            "environmentDigestMatches": model.environment_digest == calculated_environment,
            "artifactBundleHashDeclared": model.artifact_bundle_hash,
            "artifactBundleHashCalculated": calculated_bundle,
            "artifactBundleHashMatches": model.artifact_bundle_hash == calculated_bundle,
        })
    return models, sorted(assets.values(), key=lambda item: item["path"])


def simulated_autocrlf_checkout(paths: list[str]) -> Path:
    workspace = Path(tempfile.mkdtemp(prefix="shm_em_eol_validation_"))
    source = workspace / "source"
    checkout = workspace / "checkout"
    source.mkdir()
    shutil.copy2(ROOT / ".gitattributes", source / ".gitattributes")
    for relative_path in paths:
        destination = source / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative_path, destination)
    git("init", "--quiet", cwd=source)
    git("config", "user.name", "SHM-EM Revision Audit", cwd=source)
    git("config", "user.email", "revision-audit@example.invalid", cwd=source)
    git("config", "core.autocrlf", "true", cwd=source)
    git("add", ".", cwd=source)
    git("commit", "--quiet", "-m", "contract checkout fixture", cwd=source)
    subprocess.run(
        ["git", "-c", "core.autocrlf=true", "clone", "--quiet", str(source), str(checkout)],
        check=True,
        capture_output=True,
        text=True,
    )
    return checkout


def remove_readonly(function, path: str, _error) -> None:
    os.chmod(path, stat.S_IWRITE)
    function(path)


def validate() -> dict[str, Any]:
    models, assets = contract_assets()
    checkout = simulated_autocrlf_checkout([item["path"] for item in assets])
    try:
        for item in assets:
            path = ROOT / item["path"]
            clone_path = checkout / item["path"]
            current_hash = sha256_file(path)
            checkout_hash = sha256_file(clone_path)
            attrs = attributes(item["path"])
            declared = item["declaredHashes"]
            item.update({
                "currentRawSha256": current_hash,
                "autocrlfCheckoutRawSha256": checkout_hash,
                "declaredHashMatchesCurrent": not declared or all(value == current_hash for value in declared),
                "declaredHashMatchesAutocrlfCheckout": not declared or all(value == checkout_hash for value in declared),
                "currentMatchesAutocrlfCheckout": current_hash == checkout_hash,
                "gitAttributes": attrs,
                "gitEolState": eol_state(item["path"]),
                "eolPolicyMatches": (
                    attrs.get("text") == "set" and attrs.get("eol") == "lf"
                    if item["textArtifact"]
                    else attrs.get("text") == "unset"
                ),
            })
            if item["textArtifact"]:
                item["currentEolCounts"] = text_eol_counts(path)
                item["autocrlfCheckoutEolCounts"] = text_eol_counts(clone_path)
                item["lfOnlyInBothCheckouts"] = (
                    item["currentEolCounts"]["crlfCount"] == 0
                    and item["currentEolCounts"]["bareCarriageReturnCount"] == 0
                    and item["autocrlfCheckoutEolCounts"]["crlfCount"] == 0
                    and item["autocrlfCheckoutEolCounts"]["bareCarriageReturnCount"] == 0
                )
            else:
                item["binaryBytesUnaffected"] = current_hash == checkout_hash
    finally:
        shutil.rmtree(checkout.parent, onerror=remove_readonly)

    passed = (
        all(item["declaredHashMatchesCurrent"] for item in assets)
        and all(item["declaredHashMatchesAutocrlfCheckout"] for item in assets)
        and all(item["currentMatchesAutocrlfCheckout"] for item in assets)
        and all(item["eolPolicyMatches"] for item in assets)
        and all(item["environmentDigestMatches"] and item["artifactBundleHashMatches"] for item in models)
    )
    return {
        "schemaVersion": "shm-em-public-contract-hash-validation-v1",
        "hashMode": "raw-bytes-no-eol-normalization",
        "simulatedCheckout": "git clone with core.autocrlf=true",
        "sourceGitCommit": git("rev-parse", "HEAD"),
        "submittedTagCommit": git("rev-parse", "v1.0.0^{}"),
        "modelCount": len(models),
        "assetCount": len(assets),
        "passed": passed,
        "models": models,
        "assets": assets,
    }


def render_review(report: dict[str, Any]) -> str:
    rows = [
        f"| `{item['path']}` | {', '.join(item['kinds'])} | {str(item['declaredHashMatchesCurrent']).lower()} | {str(item['declaredHashMatchesAutocrlfCheckout']).lower()} | {item['gitAttributes'].get('text')} / {item['gitAttributes'].get('eol')} |"
        for item in report["assets"]
    ]
    return "\n".join([
        "# Phase 0.6.1 EOL and Public Contract Review",
        "",
        f"- Overall raw-byte validation: `{str(report['passed']).lower()}`",
        f"- Active models: `{report['modelCount']}`",
        f"- Unique contract-sensitive assets: `{report['assetCount']}`",
        "- Hash method: raw file bytes; no LF normalization is performed by the validator.",
        "- Checkout simulation: a real Git clone with `core.autocrlf=true`.",
        "",
        "| Path | Contract role | Current raw hash | autocrlf checkout raw hash | text / eol attribute |",
        "| --- | --- | --- | --- | --- |",
        *rows,
        "",
        "Binary `.pth` and `.joblib` artifacts are marked `-text`. Inference scripts, best-parameter JSON files, the runtime manifest, and the dependency lock use deterministic LF checkout bytes.",
        "",
    ])


def main() -> int:
    args = parse_args()
    output_dir = resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = validate()
    (output_dir / "public-contract-hash-validation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "eol-policy-review.md").write_text(
        render_review(report),
        encoding="utf-8",
    )
    print(json.dumps({
        "assetCount": report["assetCount"],
        "modelCount": report["modelCount"],
        "passed": report["passed"],
    }, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
