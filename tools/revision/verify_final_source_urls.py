#!/usr/bin/env python3
"""Check public URLs used by final metadata and revision sources."""

from __future__ import annotations

import concurrent.futures
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


SOURCES = (
    "CITATION.cff",
    "codemeta.json",
    "README.md",
    "docs/DATA_AVAILABILITY.md",
    "docs/RELEASE_CHECKSUMS.md",
    "manuscript/SHM-EM_Revised_Manuscript_Source.md",
    "manuscript/Response_to_Reviewers_Source.md",
    "manuscript/Final_Reviewer_Evidence_Map.md",
)
URL = re.compile(r"https?://[^\s<>`\]]+")


def check_url(url: str) -> dict[str, object]:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SHM-EM-url-verifier"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return {"url": url, "status": response.status, "reachable": response.status < 500}
    except urllib.error.HTTPError as error:
        if error.code >= 500 and url.startswith("https://doi.org/"):
            doi = url.removeprefix("https://doi.org/")
            crossref = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(crossref, headers={"User-Agent": "SHM-EM-url-verifier"}),
                    timeout=30,
                ) as response:
                    return {
                        "url": url,
                        "status": error.code,
                        "reachable": response.status == 200,
                        "registryFallback": "Crossref",
                        "registryStatus": response.status,
                    }
            except Exception as fallback_error:  # noqa: BLE001
                return {
                    "url": url,
                    "status": error.code,
                    "reachable": False,
                    "registryFallback": "Crossref",
                    "error": str(fallback_error),
                }
        return {"url": url, "status": error.code, "reachable": error.code < 500}
    except Exception as error:  # noqa: BLE001 - preserve the public preflight failure reason
        return {"url": url, "status": None, "reachable": False, "error": str(error)}


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    urls: set[str] = set()
    for relative in SOURCES:
        text = (repo / relative).read_text(encoding="utf-8")
        for match in URL.findall(text):
            urls.add(match.rstrip(".,;:)'\""))

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(check_url, sorted(urls)))
    failures = [item for item in results if not item["reachable"]]
    value = {
        "schemaVersion": "shm-em-final-source-url-validation-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "sources": list(SOURCES),
        "urlCount": len(results),
        "reachableCount": len(results) - len(failures),
        "results": results,
        "pass": not failures,
    }
    output = repo / "artifacts/revision/final-manuscript-review/final-source-url-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"pass": value["pass"], "urls": len(results), "failures": failures}, indent=2))
    return 0 if value["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
