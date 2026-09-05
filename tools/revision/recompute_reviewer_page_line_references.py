#!/usr/bin/env python3
"""Derive all reviewer locations from final PDF line numbering."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "artifacts" / "revision" / "final-submission"

SECTION_PATTERNS = {
    "abstract": r"^Abstract\s+\d+\s*$",
    "metadata": r"^Metadata\s+\d+\s*$",
    "motivation": r"^1\. Motivation and significance\s+\d+\s*$",
    "users": r"^1\.1 Intended users and experimental setup\s+\d+\s*$",
    "software": r"^2\. Software description\s+\d+\s*$",
    "architecture": r"^2\.1 Software architecture\s+\d+\s*$",
    "objects": r"^2\.1\.1 Engineering monitoring object model and observation registry\s+\d+\s*$",
    "contract": r"^2\.1\.2 Engineering-semantic data-model contract\s+\d+\s*$",
    "missing": r"^Missing and asynchronous observations\s+\d+\s*$",
    "future_state": r"^2\.1\.3 Multi-target rolling forecasts and Project Future State\s+\d+\s*$",
    "transition": r"^2\.1\.4 Controlled transition from forecasts to engineering events\s+\d+\s*$",
    "response": r"^2\.1\.5 Response, provenance, and reproduction\s+\d+\s*$",
    "functions": r"^2\.2 Main functionalities\s+\d+\s*$",
    "rules": r"^2\.3 Rule configuration and interfaces\s+\d+\s*$",
    "validation": r"^3\. Software validation\s+\d+\s*$",
    "public_case": r"^3\.1 Public excavation-monitoring reference case\s+\d+\s*$",
    "reuse": r"^3\.2 Cross-configuration reuse\s+\d+\s*$",
    "failure": r"^3\.3 Failure-path and execution-safety validation\s+\d+\s*$",
    "runtime": r"^3\.4 Runtime and bounded scalability\s+\d+\s*$",
    "provenance": r"^3\.5 Provenance and reproducibility\s+\d+\s*$",
    "impact": r"^4\. Impact\s+\d+\s*$",
    "impact_integration": r"^4\.1 Reproducible and auditable forecast integration\s+\d+\s*$",
    "impact_reuse": r"^4\.2 Cross-configuration reuse\s+\d+\s*$",
    "impact_transition": r"^4\.3 Controlled event transition and traceability\s+\d+\s*$",
    "limitations": r"^4\.4 Current deployment and scientific scope\s+\d+\s*$",
    "conclusions": r"^5\. Conclusions\s+\d+\s*$",
    "availability": r"^6\. Data and software availability\s+\d+\s*$",
    "acknowledgements": r"^Acknowledgements\s+\d+\s*$",
    "ai_declaration": r"^Declaration of generative AI and AI\s*-assisted technologies.*\s+\d+\s*$",
    "references": r"^References\s+\d+\s*$",
}

# Each tuple identifies the first and last section included in one cited range.
ITEM_RANGES = {
    "R1-0": [("abstract", "abstract"), ("software", "provenance")],
    "R1-1": [("reuse", "reuse"), ("impact_reuse", "impact_reuse")],
    "R1-2": [("validation", "provenance")],
    "R1-3": [("transition", "transition"), ("failure", "failure")],
    "R1-4": [("motivation", "motivation")],
    "R1-5": [("contract", "missing")],
    "R1-6": [("future_state", "future_state")],
    "R1-7": [("contract", "contract")],
    "R1-8": [("future_state", "future_state"), ("limitations", "conclusions")],
    "R1-9": [("runtime", "runtime")],
    "R1-10": [("runtime", "runtime"), ("limitations", "limitations")],
    "R1-11": [("limitations", "limitations")],
    "R1-12": [("provenance", "provenance"), ("limitations", "limitations")],
    "R1-13": [("transition", "transition")],
    "R1-14": [("functions", "functions")],
    "R1-15": [("reuse", "reuse"), ("impact_integration", "limitations")],
    "R1-16": [("validation", "validation")],
    "R1-17": [("provenance", "provenance")],
    "R1-18": [("motivation", "motivation"), ("limitations", "limitations")],
    "R1-19": [("motivation", "motivation"), ("conclusions", "conclusions")],
    "R2-1": [("motivation", "motivation"), ("validation", "provenance")],
    "R2-2": [("motivation", "motivation")],
    "R2-3": [("missing", "missing"), ("failure", "failure")],
    "R3-1": [("architecture", "objects"), ("runtime", "runtime"), ("limitations", "limitations")],
    "R3-2": [("limitations", "limitations")],
    "R3-3": [("contract", "missing")],
    "R3-4": [("provenance", "provenance"), ("limitations", "limitations")],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-pdf", type=Path, required=True)
    parser.add_argument("--clean-docx", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=FINAL / "reviewer-page-line-references.json")
    parser.add_argument("--verification", type=Path, default=FINAL / "reviewer-page-line-references-verification.json")
    return parser.parse_args()


def parse_document(pdf: Path):
    reader = PdfReader(str(pdf))
    line_pages: dict[int, int] = {}
    section_starts: dict[str, int] = {}
    for page_number, page in enumerate(reader.pages, start=1):
        for raw_line in (page.extract_text() or "").splitlines():
            match = re.search(r"(?:^|\s)(\d+)\s*$", raw_line)
            if match:
                number = int(match.group(1))
                if number > 0:
                    line_pages.setdefault(number, page_number)
            for key, pattern in SECTION_PATTERNS.items():
                if key not in section_starts and re.match(pattern, raw_line.strip()):
                    section_starts[key] = int(re.search(r"(\d+)\s*$", raw_line).group(1))
    missing = sorted(set(SECTION_PATTERNS) - set(section_starts))
    if missing:
        raise RuntimeError(f"Unable to locate final manuscript headings: {missing}")
    ordered = sorted(section_starts.items(), key=lambda item: item[1])
    section_ends: dict[str, int] = {}
    for index, (key, start) in enumerate(ordered):
        next_start = ordered[index + 1][1] if index + 1 < len(ordered) else max(line_pages) + 1
        section_ends[key] = next_start - 1
    return reader, line_pages, section_starts, section_ends


def page_label(start_page: int, end_page: int) -> str:
    return f"p. {start_page}" if start_page == end_page else f"pp. {start_page}-{end_page}"


def main() -> int:
    args = parse_args()
    reader, line_pages, starts, ends = parse_document(args.clean_pdf)
    references: dict[str, str] = {}
    resolved: dict[str, list[dict[str, object]]] = {}
    for item, ranges in ITEM_RANGES.items():
        labels = []
        resolved[item] = []
        for start_key, end_key in ranges:
            start_line = starts[start_key]
            end_line = ends[end_key]
            start_page = line_pages[start_line]
            end_page = line_pages[end_line]
            labels.append(f"{page_label(start_page, end_page)}, lines {start_line}-{end_line}")
            resolved[item].append({
                "startSection": start_key,
                "endSection": end_key,
                "startPage": start_page,
                "endPage": end_page,
                "startLine": start_line,
                "endLine": end_line,
            })
        references[item] = "; ".join(labels)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(references, indent=2) + "\n", encoding="utf-8")
    verification = {
        "schemaVersion": "shm-em-reviewer-page-line-verification-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "method": "Section anchors and continuous Word line numbers extracted from the final clean PDF",
        "cleanPdf": {"path": str(args.clean_pdf), "sha256": sha256(args.clean_pdf), "pages": len(reader.pages)},
        "cleanDocx": {"path": str(args.clean_docx), "sha256": sha256(args.clean_docx)},
        "reviewerItemCount": len(references),
        "sectionStarts": starts,
        "resolvedRanges": resolved,
        "pass": tuple(references) == tuple(ITEM_RANGES) and len(references) == 27,
    }
    args.verification.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": verification["pass"], "items": len(references), "pages": len(reader.pages)}, indent=2))
    return 0 if verification["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
