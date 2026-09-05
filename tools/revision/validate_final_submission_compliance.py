#!/usr/bin/env python3
"""Validate SoftwareX word, declaration, artwork, and author-owned gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


ROOT = Path(__file__).resolve().parents[2]
MANUSCRIPT = ROOT / "manuscript" / "SHM-EM_Revised_Manuscript_Source.md"
ARTWORK = ROOT / "artifacts" / "revision" / "final-submission" / "figures"
PAGE_REFS = ROOT / "artifacts" / "revision" / "final-submission" / "reviewer-page-line-references.json"
PAGE_REFS_VERIFICATION = ROOT / "artifacts" / "revision" / "final-submission" / "reviewer-page-line-references-verification.json"
MANUAL = ROOT / "manuscript" / "Final_Author_Editorial_Checks.json"
OUTPUT = ROOT / "artifacts" / "revision" / "final-submission" / "final-submission-compliance.json"

AI_HEADING = "Declaration of generative AI and AI-assisted technologies in the manuscript preparation process"
REVIEWER_IDS = (
    "R1-0",
    *(f"R1-{index}" for index in range(1, 20)),
    *(f"R2-{index}" for index in range(1, 4)),
    *(f"R3-{index}" for index in range(1, 5)),
)
FIGURE_CAPTIONS = {
    1: "Fig. 1. Research gaps, the SHM-EM software boundary, and the forecast-aware user workflow.",
    2: "Fig. 2. Four-layer SHM-EM architecture. MySQL is the validated reference persistence implementation; the observation registry and service interfaces define the storage-adapter extension boundary.",
    3: "Fig. 3. Controlled sequence from persisted forecasts through optional Project Future State inspection, audited Evaluate, independently gated Execute, and formal provenance.",
    4: "Fig. 4. Task-oriented interface views of SHM-EM: project-level observed and forecast risk, a joint engineering-valued observation/forecast series, and prediction-batch completeness and execution eligibility. The interface is illustrative; quantitative validation is reported separately.",
    5: "Fig. 5. Public reference case, verified six-model contract, common temporal frame, and end-to-end reproduction checks.",
}
SUBMISSION_ARTWORK = {
    1: "Fig1_Research_Gap_and_Workflow.pdf",
    2: "Fig2_Software_Architecture.pdf",
    3: "Fig3_Forecast_to_Event_Sequence.pdf",
    4: "Fig4_Task_Oriented_Interface_Composite.tiff",
    5: "Fig5_Public_Reference_Workflow.tiff",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-docx", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return parser.parse_args()


def visible_word_count(text: str) -> int:
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[#*`>|\[\]{}(),;:]", " ", text)
    return sum(1 for token in re.split(r"\s+", text) if re.search(r"[A-Za-z0-9]", token))


def source_submission_text(source: str) -> str:
    body = source.split("## Abstract", 1)[1].split("# References", 1)[0]
    before_metadata, after_metadata = body.split("## Metadata", 1)
    after_metadata = after_metadata.split("# 1. Motivation and significance", 1)[1]
    body = "Abstract\n" + before_metadata + "\n1. Motivation and significance\n" + after_metadata
    for number, caption in FIGURE_CAPTIONS.items():
        body = re.sub(
            rf">\s*\*\*Figure\s+{number}\s+insertion note\.\*\*[^\n]*",
            caption,
            body,
        )
    return body


def iter_docx_blocks(document: Document):
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            texts = [node.text or "" for node in child.iter(qn("w:t"))]
            yield "paragraph", "".join(texts).strip()
        elif child.tag == qn("w:tbl"):
            cells = []
            for cell in child.iter(qn("w:tc")):
                texts = [node.text or "" for node in cell.iter(qn("w:t"))]
                cells.append(" ".join(part for part in texts if part).strip())
            yield "table", " ".join(value for value in cells if value)


def docx_submission_text(path: Path) -> tuple[str, list[str], int]:
    document = Document(path)
    capture = False
    skip_metadata = False
    parts: list[str] = []
    headings: list[str] = []
    figure_count = 0
    for kind, text in iter_docx_blocks(document):
        if not text:
            continue
        if kind == "paragraph" and text == "Abstract":
            capture = True
        if not capture:
            continue
        if kind == "paragraph" and text == "Metadata":
            skip_metadata = True
            continue
        if kind == "paragraph" and text == "1. Motivation and significance":
            skip_metadata = False
        if kind == "paragraph" and text == "References":
            break
        if skip_metadata:
            continue
        if kind == "paragraph" and text in {AI_HEADING, "References"}:
            headings.append(text)
        if kind == "paragraph" and re.match(r"^Fig\.\s+[1-5]\.", text):
            figure_count += 1
        parts.append(text)
    return "\n".join(parts), headings, figure_count


def gate(identifier: str, passed: bool, detail: str) -> dict[str, object]:
    return {"id": identifier, "status": "PASS" if passed else "FAIL", "detail": detail}


def main() -> int:
    args = parse_args()
    source = MANUSCRIPT.read_text(encoding="utf-8")
    source_text = source_submission_text(source)
    source_count = visible_word_count(source_text)

    counted_text = source_text
    count_basis = "Markdown source with final captions substituted"
    figure_count = len(re.findall(r"Figure\s+[1-5]\s+insertion note", source))
    if args.clean_docx:
        counted_text, _, figure_count = docx_submission_text(args.clean_docx)
        count_basis = f"Final clean DOCX: {args.clean_docx}"
    strict_count = visible_word_count(counted_text)

    section_before_references = source.split("# References", 1)[0].rstrip()
    declaration_present = section_before_references.endswith(
        "The authors take full responsibility for the publication's content."
    ) and f"# {AI_HEADING}" in section_before_references

    artwork_presence = {number: (ARTWORK / name).is_file() for number, name in SUBMISSION_ARTWORK.items()}
    artwork_formats = all(
        Path(name).suffix.lower() in ({".pdf"} if number <= 3 else {".tif", ".tiff", ".jpg", ".jpeg"})
        for number, name in SUBMISSION_ARTWORK.items()
    )
    refs = json.loads(PAGE_REFS.read_text(encoding="utf-8")) if PAGE_REFS.is_file() else {}
    refs_complete = tuple(refs.keys()) == REVIEWER_IDS and all(str(value).strip() for value in refs.values())
    refs_verification = (
        json.loads(PAGE_REFS_VERIFICATION.read_text(encoding="utf-8"))
        if PAGE_REFS_VERIFICATION.is_file()
        else {}
    )
    refs_current = bool(
        args.clean_docx
        and refs_verification.get("pass") is True
        and refs_verification.get("reviewerItemCount") == 27
        and refs_verification.get("cleanDocx", {}).get("sha256") == sha256(args.clean_docx)
    )

    automated = [
        gate("FS-01", strict_count <= 3000, f"Strict count {strict_count}; source preflight {source_count}; recommended target <=2900: {strict_count <= 2900}."),
        gate("FS-02", figure_count <= 6 and figure_count == 5, f"Final manuscript figure count: {figure_count}."),
        gate("FS-03", declaration_present, "Required AI declaration is immediately before References in the source."),
        gate("FS-04", all(artwork_presence.values()), f"Separate submission artwork present: {artwork_presence}."),
        gate("FS-05", artwork_formats and all(artwork_presence.values()), "Fig. 1-3 use PDF; Fig. 4-5 use TIFF submission copies."),
        gate("FS-06", refs_complete and refs_current, f"Page/line map contains {len(refs)} ordered references and is bound to the final clean DOCX: {refs_current}."),
    ]

    manual_source = json.loads(MANUAL.read_text(encoding="utf-8"))
    manual = [
        {"id": identifier, **manual_source[identifier]}
        for identifier in ("FS-07", "FS-08", "FS-09", "FS-10")
    ]
    automated_pass = all(item["status"] == "PASS" for item in automated)
    manual_pass = all(item["status"] == "PASS" for item in manual)
    result = {
        "schemaVersion": "shm-em-final-submission-compliance-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "countBasis": count_basis,
        "strictWordCount": strict_count,
        "sourcePreflightWordCount": source_count,
        "automatedGates": automated,
        "manualGates": manual,
        "automatedPass": automated_pass,
        "submissionReady": automated_pass and manual_pass,
        "submissionStatus": "READY" if automated_pass and manual_pass else "HOLD_FOR_MANUAL_CONFIRMATION" if automated_pass else "HOLD_FOR_AUTOMATED_CORRECTION",
    }
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if automated_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
