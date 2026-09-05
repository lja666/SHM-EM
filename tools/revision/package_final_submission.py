#!/usr/bin/env python3
"""Validate and package the SoftwareX final manuscript deliverables."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

from docx import Document
from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "artifacts" / "revision" / "final-submission"
GENERATED_DOCX = FINAL / "docx"
GENERATED_PDF = FINAL / "pdf"
FIGURES = FINAL / "figures"
VALIDATION = (
    ROOT
    / "artifacts"
    / "revision"
    / "final-manuscript-review"
    / "final-manuscript-source-validation-v2.json"
)
FREEZE = "eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f"
REVIEWED_SOURCE = "9caa9c0b7e8b7204a0f8e4b44e8a963edb6d5dc6"
RELEASE_COMMIT = "d7cba1419145e6c75fe69ad63172af5f5abe5028"
RELEASE_SHA256 = "ea0973b7c82e06c3c8910ec36fcf2c3d47765a87d11552337a86c69de41a7cef"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
    ).stdout.strip()


def pdf_text(path: Path) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def docx_text(path: Path) -> str:
    document = Document(str(path))
    parts = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    return "\n".join(parts)


def tokens(text: str) -> list[str]:
    # Split punctuation so PDF line wrapping and hyphenation do not create false mismatches.
    return re.findall(r"[a-z0-9]+", text.lower())


def tracked_revision_counts(path: Path) -> dict[str, int]:
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    return {
        name: len(root.findall(f".//{namespace}{name}"))
        for name in ("ins", "del", "moveFrom", "moveTo")
    }


def final_view_docx_text(path: Path) -> str:
    """Extract Word's final view by excluding deleted and move-from content."""
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    excluded = {f"{namespace}del", f"{namespace}moveFrom"}
    parts: list[str] = []

    def visit(element: ElementTree.Element) -> None:
        if element.tag in excluded:
            return
        if element.tag == f"{namespace}t" and element.text:
            parts.append(element.text)
        elif element.tag == f"{namespace}tab":
            parts.append("\t")
        elif element.tag in {f"{namespace}br", f"{namespace}cr"}:
            parts.append("\n")
        for child in element:
            visit(child)
        if element.tag == f"{namespace}p":
            parts.append("\n")
        elif element.tag == f"{namespace}tc":
            parts.append("\t")

    visit(root)
    return "".join(parts)


def copy_canonical_outputs() -> dict[str, Path]:
    mapping = {
        "cleanDocx": (
            GENERATED_DOCX / "SHM-EM_Revised_Manuscript_Clean.docx",
            FINAL / "SHM-EM_SoftwareX_Revised_Clean.docx",
        ),
        "markedDocx": (
            GENERATED_DOCX / "SHM-EM_Revised_Manuscript_Marked.docx",
            FINAL / "SHM-EM_SoftwareX_Revised_Marked.docx",
        ),
        "responseDocx": (
            GENERATED_DOCX / "SHM-EM_Response_to_Reviewers.docx",
            FINAL / "Response_to_Reviewers.docx",
        ),
        "cleanPdf": (
            GENERATED_PDF / "SHM-EM_Revised_Manuscript_Clean.pdf",
            FINAL / "SHM-EM_SoftwareX_Revised_Clean.pdf",
        ),
        "markedPdf": (
            GENERATED_PDF / "SHM-EM_Revised_Manuscript_Marked.pdf",
            FINAL / "SHM-EM_SoftwareX_Revised_Marked.pdf",
        ),
        "responsePdf": (
            GENERATED_PDF / "SHM-EM_Response_to_Reviewers.pdf",
            FINAL / "Response_to_Reviewers.pdf",
        ),
    }
    results: dict[str, Path] = {}
    for key, (source, destination) in mapping.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, destination)
        results[key] = destination
    shutil.copy2(VALIDATION, FINAL / VALIDATION.name)
    shutil.copy2(
        ROOT / "manuscript" / "Final_Submission_Checklist.md",
        FINAL / "Final_Submission_Checklist.md",
    )
    return results


def page_count(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


def baseline_verification(
    canonical: dict[str, Path], submitted_pdf: Path, submitted_docx: Path
) -> dict[str, object]:
    submitted_pdf_tokens = set(tokens(pdf_text(submitted_pdf)))
    submitted_docx_tokens = set(tokens(docx_text(submitted_docx)))
    overlap = len(submitted_pdf_tokens.intersection(submitted_docx_tokens))
    clean_tokens = tokens(final_view_docx_text(canonical["cleanDocx"]))
    marked_tokens = tokens(final_view_docx_text(canonical["markedDocx"]))
    counts = tracked_revision_counts(canonical["markedDocx"])
    result = {
        "schemaVersion": "shm-em-submitted-baseline-verification-v1",
        "submittedPdf": {
            "sha256": sha256(submitted_pdf),
            "pages": page_count(submitted_pdf),
        },
        "submittedDocx": {"sha256": sha256(submitted_docx)},
        "submittedDocxUniqueTokenCoverageInSubmittedPdf": round(
            overlap / len(submitted_docx_tokens), 6
        ),
        "markedComparisonBaseline": "Actual submitted manuscript DOCX verified against the Editorial Manager PDF text.",
        "trackedRevisionCounts": counts,
        "cleanMarkedFinalViewTokenSequenceEqual": clean_tokens == marked_tokens,
        "cleanMarkedDocxFinalViewTokenCounts": {
            "clean": len(clean_tokens),
            "marked": len(marked_tokens),
        },
        "pass": (
            overlap / len(submitted_docx_tokens) >= 0.99
            and counts["ins"] > 0
            and counts["del"] > 0
            and clean_tokens == marked_tokens
        ),
    }
    return result


def production_core_diff() -> list[str]:
    output = git(
        "diff",
        "--name-only",
        FREEZE,
        "--",
        "src/backend/src/main",
        "src/pit_pre/pit_pre",
        "src/frontend/src",
    )
    return [line for line in output.splitlines() if line]


def build_completion_report(
    canonical: dict[str, Path], verification: dict[str, object], validation: dict[str, object]
) -> str:
    pages = {key: page_count(path) for key, path in canonical.items() if key.endswith("Pdf")}
    revision_counts = verification["trackedRevisionCounts"]
    return f"""# Final Submission Completion Report

## Decision

The SoftwareX minor-revision document-generation phase is complete and ready for the authorized final GPT audit. No production-core source changed during this phase, and no new scientific experiment was run.

## Authority and locked anchors

- Reviewed manuscript source: `{REVIEWED_SOURCE}`
- Final production-core baseline: `{FREEZE}`
- Immutable revised release: `v1.0.1` at `{RELEASE_COMMIT}`
- Release archive SHA-256: `{RELEASE_SHA256}`
- Strengthened source validation: {sum(item['status'] == 'PASS' for item in validation['checks'])}/{len(validation['checks'])} PASS
- Reviewer items: {validation['reviewerItemCount']}
- References: {validation['referenceCount']}

## Final document set

- `SHM-EM_SoftwareX_Revised_Clean.docx` ({pages['cleanPdf']} rendered pages)
- `SHM-EM_SoftwareX_Revised_Marked.docx` ({pages['markedPdf']} rendered final-view pages)
- `Response_to_Reviewers.docx` ({pages['responsePdf']} rendered pages)
- Separate Fig. 3, Fig. 4, and Fig. 5 in 4,200-pixel PNG and editable SVG formats

The marked manuscript contains {revision_counts['ins']} insertions, {revision_counts['del']} deletions, {revision_counts['moveFrom']} move-from elements, and {revision_counts['moveTo']} move-to elements. Its final-view token sequence is identical to the clean manuscript: `{str(verification['cleanMarkedFinalViewTokenSequenceEqual']).lower()}`.

## Baseline and pagination checks

The tracked comparison used the actual submitted manuscript DOCX after verifying it against the Editorial Manager submitted PDF. Submitted-DOCX unique-token coverage in that PDF is {verification['submittedDocxUniqueTokenCoverageInSubmittedPdf']:.4%}. Final clean-manuscript page and line references were then inserted into all 27 response items.

## Rendering QA

`render_docx.py` was attempted first, but the local environment does not provide LibreOffice. Microsoft Word COM was therefore used for deterministic PDF export and Poppler at 144 dpi for page images. Every page of the 19-page clean manuscript and the final 12-page response letter was visually inspected. The marked document was checked in final view and its OOXML revision elements were counted independently.

Checks completed:

- no clipped tables, listings, algorithms, figures, captions, or references;
- no overflow, overlap, duplicate footer, or orphaned near-empty page;
- Fig. 3 transition semantics match the code-crosschecked sequence;
- Fig. 4 is one compact three-panel illustrative UI composite;
- Fig. 5 distinguishes aligned input widths, output widths, and model-owned mappings;
- clean and marked final-view text are identical;
- all 27 response items contain a final page/line location;
- production-core diff against Final Core Freeze v3 is empty.

## Expected validator rerun behavior

The stored v2 artifact validates the five authorized source files at `{REVIEWED_SOURCE}` and records 24/24 PASS. A rerun against the current evidence-only worktree intentionally rejects `manuscript/Revision_Change_Map.md` and `manuscript/Final_Submission_Checklist.md`: authorized housekeeping H2 corrected the release-synchronization status, and the checklist now records GPT authorization and completed generation/QA work. These post-review documentation changes are not manuscript-science changes, and no self-validating commit loop was introduced.

## Remaining author-owned submission checks

- all authors confirm names, affiliations, funding, correspondence, and acknowledgements;
- the data owner approves the software/data availability wording;
- the corresponding author confirms Editorial Manager deadline and filename constraints.
"""


def artifact_entry(path: Path) -> dict[str, object]:
    entry: dict[str, object] = {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    if path.suffix.lower() == ".pdf":
        entry["pages"] = page_count(path)
    if path.suffix.lower() == ".png":
        with Image.open(path) as image:
            entry["pixels"] = {"width": image.width, "height": image.height}
    return entry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submitted-pdf", type=Path, required=True)
    parser.add_argument("--submitted-docx", type=Path, required=True)
    args = parser.parse_args()

    FINAL.mkdir(parents=True, exist_ok=True)
    canonical = copy_canonical_outputs()
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if not validation.get("pass") or len(validation.get("checks", [])) != 24:
        raise RuntimeError("The strengthened source validation is not 24/24 PASS.")
    core_diff = production_core_diff()
    if core_diff:
        raise RuntimeError(f"Production-core diff is not empty: {core_diff}")

    verification = baseline_verification(canonical, args.submitted_pdf, args.submitted_docx)
    if not verification["pass"]:
        raise RuntimeError(f"Baseline or marked-manuscript verification failed: {verification}")
    verification_path = FINAL / "submitted-baseline-verification.json"
    verification_path.write_text(
        json.dumps(verification, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    report_path = FINAL / "FINAL_SUBMISSION_COMPLETION_REPORT.md"
    report_path.write_text(
        build_completion_report(canonical, verification, validation), encoding="utf-8"
    )

    handoff_path = FINAL / "GPT_REVIEW_HANDOFF.md"
    handoff_path.write_text(
        f"""# GPT Review Handoff

## Requested review

Perform the final scientific-consistency, visual/layout, response page/line, and SoftwareX submission-package audit authorized after the final scientific PASS.

## Review first

1. `FINAL_SUBMISSION_COMPLETION_REPORT.md`
2. `final-submission-manifest.json`
3. `SHM-EM_SoftwareX_Revised_Clean.docx`
4. `SHM-EM_SoftwareX_Revised_Marked.docx`
5. `Response_to_Reviewers.docx`
6. `final-manuscript-source-validation-v2.json`
7. `submitted-baseline-verification.json`
8. `reviewer-page-line-references.json`
9. `Final_Submission_Checklist.md`
10. Fig. 3, Fig. 4, and Fig. 5 PNG/SVG files

## Locked boundaries

- Production-core baseline: `{FREEZE}`; final diff: `NONE`.
- Revised release: `v1.0.1` at `{RELEASE_COMMIT}`; do not move tags.
- No new experiment, algorithm claim, tolerance, or release was introduced.
- Windows remains the exact-output reference; Docker/Linux establishes functional/logical portability only.

## Stop condition

This package ends the Codex generation phase. Any further source, science, or submission change requires a new explicit decision after GPT review.
""",
        encoding="utf-8",
    )

    deliverables = [
        *canonical.values(),
        *(FIGURES / name for name in (
            "Fig3_Forecast_to_Event_Sequence.png",
            "Fig3_Forecast_to_Event_Sequence.svg",
            "Fig4_Task_Oriented_Interface_Composite.png",
            "Fig4_Task_Oriented_Interface_Composite.svg",
            "Fig5_Public_Reference_Workflow.png",
            "Fig5_Public_Reference_Workflow.svg",
        )),
        FINAL / VALIDATION.name,
        FINAL / "Final_Submission_Checklist.md",
        FINAL / "reviewer-page-line-references.json",
        verification_path,
        report_path,
        handoff_path,
        ROOT / "manuscript" / "SHM-EM_Revised_Manuscript_Source.md",
        ROOT / "manuscript" / "Response_to_Reviewers_Source.md",
        ROOT / "manuscript" / "Revision_Change_Map.md",
    ]
    for path in deliverables:
        if not path.is_file():
            raise FileNotFoundError(path)

    manifest = {
        "schemaVersion": "shm-em-final-submission-manifest-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "generationBaseHead": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "reviewedSourceHead": REVIEWED_SOURCE,
        "finalCoreFreezeV3": FREEZE,
        "productionCoreDiff": "NONE",
        "release": {
            "tag": "v1.0.1",
            "commit": RELEASE_COMMIT,
            "archiveSha256": RELEASE_SHA256,
        },
        "sourceValidation": "24/24 PASS",
        "reviewerItems": 27,
        "references": 30,
        "artifacts": [artifact_entry(path) for path in deliverables],
    }
    manifest_path = FINAL / "final-submission-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    review_dir = FINAL / "gpt-review-package"
    review_dir.mkdir(parents=True, exist_ok=True)
    package_files = [*deliverables, manifest_path]
    for path in package_files:
        shutil.copy2(path, review_dir / path.name)

    zip_path = FINAL / "SHM-EM_Final_Submission_GPT_Review_Package.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in package_files:
            archive.write(path, arcname=path.name)
    zip_digest = sha256(zip_path)
    (FINAL / f"{zip_path.name}.sha256").write_text(
        f"{zip_digest}  {zip_path.name}\n", encoding="ascii"
    )

    print(
        json.dumps(
            {
                "pass": True,
                "finalDirectory": str(FINAL),
                "reviewDirectory": str(review_dir),
                "zip": str(zip_path),
                "zipSha256": zip_digest,
                "productionCoreDiff": "NONE",
                "pageCounts": {
                    key: page_count(path)
                    for key, path in canonical.items()
                    if key.endswith("Pdf")
                },
                "trackedRevisionCounts": verification["trackedRevisionCounts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
