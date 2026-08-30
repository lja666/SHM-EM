#!/usr/bin/env python3
"""Build the bounded GPT review package for the Phase 1A.1 stop point."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess


SOURCE_FILES = [
    "sql/shm_em_database/00_SHM_EM_complete_schema.sql",
    "sql/shm_em_database/04_SHM_EM_persisted_prediction_integrity.sql",
    "sql/shm_em_database/README.md",
    "src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/PersistedPredictionIntegrityHashService.java",
    "src/backend/src/main/java/mybatis/iem/em/modules/engineering/application/service/impl/PredictionExecutionGateServiceImpl.java",
    "src/backend/src/main/java/mybatis/iem/em/modules/engineering/domain/model/PredictionBatch.java",
    "src/backend/src/main/java/mybatis/iem/em/modules/engineering/domain/model/PredictionDisplay.java",
    "src/backend/src/main/java/mybatis/iem/em/modules/engineering/domain/model/PredictionExecutionGate.java",
    "src/backend/src/main/java/mybatis/iem/em/modules/engineering/domain/model/PredictionRun.java",
    "src/backend/src/main/resources/mapper/modules/engineering/PredictionExecutionGateMapper.xml",
    "src/backend/src/test/java/mybatis/iem/em/modules/engineering/application/service/impl/PersistedPredictionIntegrityHashServiceTest.java",
    "src/backend/src/test/java/mybatis/iem/em/modules/engineering/application/service/impl/PredictionExecutionGateServiceImplTest.java",
    "src/pit_pre/pit_pre/result_writer.py",
    "src/pit_pre/tests/fixtures/persisted-integrity-fixture.json",
    "src/pit_pre/tests/test_persisted_integrity.py",
    "tools/revision/backfill_persisted_integrity.py",
    "tools/revision/build_final_change_inventory.py",
    "tools/revision/build_phase1a1_review_package.py",
    "tools/revision/persisted_integrity_reference.py",
    "tools/revision/run_failure_matrix.py",
    "tools/revision/verify_phase1a1_integrity.py",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    phase = repo / "artifacts" / "revision" / "phase1a_1"
    package = phase / "gpt-review-package"
    archive = phase / "SHM-EM_Phase1A1_GPT_Review_Package.zip"
    if package.exists():
        shutil.rmtree(package)
    if archive.exists():
        archive.unlink()
    package.mkdir(parents=True)

    for name in (
        "PHASE1A1_COMPLETION_REPORT.md",
        "GPT_REVIEW_HANDOFF.md",
        "regression-and-performance.json",
        "schema-migration-validation.json",
    ):
        shutil.copy2(phase / name, package / name)

    failure = phase / "failure-path-v2"
    for name in (
        "failure-matrix-v2.csv", "failure-matrix-v2.json", "failure-matrix-v2.md",
        "regression-tests.json", "production-core-diff.json", "phase1a1-manifest-v2.json",
    ):
        target = package / "failure-path" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(failure / name, target)
    for case_id in ("P00", "F05", "F09", "F12", "I01"):
        shutil.copytree(failure / "cases" / case_id, package / "failure-path" / "cases" / case_id)

    for relative in SOURCE_FILES:
        source = repo / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        target = package / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    diff = subprocess.run(
        ["git", "diff", "--binary", "HEAD", "--", *SOURCE_FILES],
        cwd=repo, text=True, capture_output=True, check=True,
    ).stdout
    (package / "tracked-changes.patch").write_text(diff, encoding="utf-8", newline="\n")
    status = subprocess.run(
        ["git", "status", "--short"], cwd=repo, text=True, capture_output=True, check=True,
    ).stdout
    (package / "git-status.txt").write_text(status, encoding="utf-8", newline="\n")

    files = []
    for path in sorted(package.rglob("*")):
        if path.is_file() and path.name != "review-package-manifest.json":
            files.append({
                "path": path.relative_to(package).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    manifest = {
        "schemaVersion": "shm-em-phase1a1-gpt-review-package-v1",
        "phase1aEvidenceCommit": "dba3109",
        "productionFixCommitted": False,
        "finalCoreFreezeV2Created": False,
        "sourceFileCount": len(SOURCE_FILES),
        "fileCountExcludingManifest": len(files),
        "files": files,
    }
    (package / "review-package-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n",
    )
    shutil.make_archive(str(archive.with_suffix("")), "zip", package)
    print(json.dumps({
        "package": str(package),
        "archive": str(archive),
        "archiveSha256": sha256(archive),
        "files": len(files) + 1,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
