# Public Validation Evidence

This directory contains the compact, public evidence needed to inspect the
claims made for SHM-EM 1.0.1. It is intentionally smaller than the local
benchmark and journal-submission workspaces from which the files were selected.

## Scope

| Directory | Evidence |
|---|---|
| `model-contract` | Database-derived model contract, dimensional reconciliation, input-alignment audit, and hash validation |
| `verification` | Automated test summaries, failure matrix, future-state boundaries, and result-equivalence checks |
| `performance` | Reference workflow timings, scaling measurements, corrected Gate timings, and controlled A/B results |
| `provenance` | One machine-readable forecast-to-event trace with its readable summary |
| `portability` | Ubuntu, Compose, security-scan, and Windows/Linux comparison results |
| `reuse` | The public second-configuration onboarding and end-to-end validation record |
| `related-software` | Source-grounded comparison data used by the SoftwareX revision |

## Excluded Material

The repository does not track generated DOCX/PDF files, screenshots, backend
logs, temporary database snapshots, GPT handoff packages, phase review ZIPs, or
duplicate benchmark captures. Running the reproduction and validation tools may
create such files under the ignored `artifacts/` directory.

The evidence here uses only the public sample and published model bundles. The
restricted full monitoring history is not included.

Machine-readable records preserve the tool and workspace paths captured during
the reported run. Those fields document the execution environment; they are
not required installation locations.
