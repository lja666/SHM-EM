# GPT Review Handoff

## Status

`AUTOMATED_COMPLIANCE_PASS / HOLD_FOR_MANUAL_CONFIRMATION`

Perform the final upload-readiness audit of the SoftwareX minor-revision package. Do not infer that FS-07 through FS-10 are complete.

## Review first

1. `FINAL_SUBMISSION_COMPLETION_REPORT.md`
2. `final-submission-manifest.json`
3. `final-submission-compliance.json`
4. `SHM-EM_SoftwareX_Revised_Clean.docx`
5. `SHM-EM_SoftwareX_Revised_Marked.docx`
6. `Response_to_Reviewers.docx`
7. `Highlights.docx`
8. `final-manuscript-source-validation-v3.json`
9. `submitted-baseline-verification.json`
10. `reviewer-page-line-references-verification.json`
11. `submission-artwork-manifest.json` and Fig. 1-Fig. 5 submission files
12. `Final_Author_Editorial_Checks.json`

## Audit questions

- Does the clean manuscript remain within 3,000 words under the conservative count?
- Is the AI declaration immediately before References?
- Are all 27 response locations supported by the 13-page clean manuscript?
- Does accepting all tracked revisions produce the clean manuscript exactly?
- Are Fig. 1-3 vector PDF and Fig. 4-5 TIFF at at least 500 dpi?
- Are all scientific claims, release anchors, and non-claims still consistent?
- Are FS-07 through FS-10 clearly left for the responsible humans?

## Locked boundaries

- Production-core baseline: `eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f`; final diff: `NONE`.
- Revised release: `v1.0.1` at `d7cba1419145e6c75fe69ad63172af5f5abe5028`; do not move tags.
- No new experiment, model, algorithm claim, tolerance, or release was introduced.
- Windows remains the exact-output reference; Docker/Linux establishes functional/logical portability only.

## Package path rule

The review directory and ZIP are generated only under `artifacts/revision/final-submission/` in this repository. No sandbox or external attachment path is authoritative.
