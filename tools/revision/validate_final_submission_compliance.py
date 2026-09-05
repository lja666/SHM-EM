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
AI_PROVENANCE = ROOT / "artifacts" / "revision" / "final-submission" / "AI_FIGURE_PROVENANCE.json"
OUTPUT = ROOT / "artifacts" / "revision" / "final-submission" / "final-submission-compliance.json"

AI_HEADING = "Declaration of generative AI and AI-assisted technologies in the manuscript preparation process"
REVIEWER_IDS = (
    "R1-0",
    *(f"R1-{index}" for index in range(1, 20)),
    *(f"R2-{index}" for index in range(1, 4)),
    *(f"R3-{index}" for index in range(1, 5)),
)
FIGURE_CAPTIONS = {
    1: "Fig. 1. Research gaps, the SHM-EM software boundary, and the forecast-aware user workflow. OpenAI Codex (model/version unrecorded) assisted layout; authors verified content.",
    2: "Fig. 2. Four-layer SHM-EM architecture. MySQL is the validated reference persistence implementation; registry and service interfaces define the storage-adapter boundary. OpenAI Codex (model/version unrecorded) assisted layout; authors checked the software boundaries.",
    3: "Fig. 3. Controlled sequence from persisted forecasts through optional Project Future State inspection, audited Evaluate, independently gated Execute, and formal provenance. OpenAI Codex (model/version unrecorded) assisted layout; authors checked the code-derived sequence.",
    4: "Fig. 4. SHM-EM views of (a) project risk, (b) a joint observation/forecast series, and (c) batch completeness and eligibility. OpenAI Codex (model/version unrecorded) assisted cropping/composition; panels derive from application captures, with AI-assisted label removal/upscaling in (a). Authors verified displayed content.",
    5: "Fig. 5. Public reference case, six-model contract, common timeline, and reproduction checks. The left conceptual panel used OpenAI ChatGPT image generation (model/version unrecorded); OpenAI Codex assisted composition. Authors verified technical labels.",
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
    declaration_marker = f"# {AI_HEADING}"
    declaration_body = (
        section_before_references.rsplit(declaration_marker, 1)[-1].strip()
        if declaration_marker in section_before_references
        else ""
    )
    declaration_present = bool(
        declaration_marker in section_before_references
        and declaration_body
        and declaration_body.endswith("take full responsibility for the publication's content.")
        and "# " not in declaration_body
    )

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

    provenance = json.loads(AI_PROVENANCE.read_text(encoding="utf-8")) if AI_PROVENANCE.is_file() else {}
    provenance_figures = provenance.get("figures", [])
    provenance_complete = bool(
        provenance.get("schemaVersion") == "shm-em-ai-figure-provenance-v1"
        and [item.get("figure") for item in provenance_figures] == [1, 2, 3, 4, 5]
        and all(
            item.get("sourceMaterial")
            and item.get("howAiAssisted")
            and item.get("notAiGenerated")
            and item.get("humanVerification")
            and item.get("finalDeterministicSource")
            and item.get("aiTools")
            and all(
                tool.get("service")
                and tool.get("modelVersion") is None
                and tool.get("modelVersionStatus") == "NOT_RETAINED"
                for tool in item["aiTools"]
            )
            for item in provenance_figures
        )
    )
    caption_disclosures = all(
        "OpenAI" in caption
        and "author" in caption.lower()
        and (not args.clean_docx or caption in counted_text)
        for caption in FIGURE_CAPTIONS.values()
    )
    figure_declaration = (
        "explanatory-figure drafting/layout" in source
        and (not args.clean_docx or "explanatory-figure drafting/layout" in counted_text)
    )
    code_method_sentence = (
        "Revision-stage code edits assisted by OpenAI Codex (model/version unrecorded) were human-reviewed "
        "and subjected to the regression and reproduction checks reported here."
    )
    code_method_disclosure = (
        code_method_sentence in source.split("## 3.5 Provenance and reproducibility", 1)[-1].split("# 4. Impact", 1)[0]
        and (not args.clean_docx or code_method_sentence in counted_text)
    )

    automated = [
        gate("FS-01", strict_count <= 3000, f"Strict count {strict_count}; source preflight {source_count}; post-disclosure target <=2950: {strict_count <= 2950}."),
        gate("FS-02", figure_count <= 6 and figure_count == 5, f"Final manuscript figure count: {figure_count}."),
        gate("FS-03", declaration_present, "Required AI declaration is immediately before References in the source."),
        gate("FS-04", all(artwork_presence.values()), f"Separate submission artwork present: {artwork_presence}."),
        gate("FS-05", artwork_formats and all(artwork_presence.values()), "Fig. 1-3 use PDF; Fig. 4-5 use TIFF submission copies."),
        gate("FS-06", refs_complete and refs_current, f"Page/line map contains {len(refs)} ordered references and is bound to the final clean DOCX: {refs_current}."),
        gate("FS-11", provenance_complete and caption_disclosures and figure_declaration, "AI figure provenance covers Fig. 1-5; each caption discloses the applicable tool/use and author verification; the general declaration includes figure assistance."),
        gate("FS-12", code_method_disclosure, "Section 3.5 discloses revision-stage AI-assisted code editing, human review, and regression/reproduction checking."),
        gate("FS-13", strict_count <= 3000, f"Post-disclosure strict count is {strict_count} words (target <=2950: {strict_count <= 2950})."),
        gate("FS-14", refs_complete and refs_current, f"Post-disclosure page/line map contains and verifies {len(refs)} reviewer locations."),
    ]

    manual_source = json.loads(MANUAL.read_text(encoding="utf-8"))
    manual = [
        {"id": identifier, **manual_source[identifier]}
        for identifier in ("FS-07A", "FS-07B", "FS-08", "FS-09", "FS-10")
    ]
    automated_pass = all(item["status"] == "PASS" for item in automated)
    manual_pass = all(item["status"] == "PASS" for item in manual)
    result = {
        "schemaVersion": "shm-em-final-submission-compliance-v2",
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
