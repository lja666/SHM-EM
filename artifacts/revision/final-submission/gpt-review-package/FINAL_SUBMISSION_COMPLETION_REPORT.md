# Final Submission Completion Report

## Decision

The SoftwareX minor-revision document-generation phase is complete and ready for the authorized final GPT audit. No production-core source changed during this phase, and no new scientific experiment was run.

## Authority and locked anchors

- Reviewed manuscript source: `9caa9c0b7e8b7204a0f8e4b44e8a963edb6d5dc6`
- Final production-core baseline: `eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f`
- Immutable revised release: `v1.0.1` at `d7cba1419145e6c75fe69ad63172af5f5abe5028`
- Release archive SHA-256: `ea0973b7c82e06c3c8910ec36fcf2c3d47765a87d11552337a86c69de41a7cef`
- Strengthened source validation: 24/24 PASS
- Reviewer items: 27
- References: 30

## Final document set

- `SHM-EM_SoftwareX_Revised_Clean.docx` (19 rendered pages)
- `SHM-EM_SoftwareX_Revised_Marked.docx` (19 rendered final-view pages)
- `Response_to_Reviewers.docx` (12 rendered pages)
- Separate Fig. 3, Fig. 4, and Fig. 5 in 4,200-pixel PNG and editable SVG formats

The marked manuscript contains 1248 insertions, 435 deletions, 4 move-from elements, and 4 move-to elements. Its final-view token sequence is identical to the clean manuscript: `true`.

## Baseline and pagination checks

The tracked comparison used the actual submitted manuscript DOCX after verifying it against the Editorial Manager submitted PDF. Submitted-DOCX unique-token coverage in that PDF is 99.3488%. Final clean-manuscript page and line references were then inserted into all 27 response items.

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

The stored v2 artifact validates the five authorized source files at `9caa9c0b7e8b7204a0f8e4b44e8a963edb6d5dc6` and records 24/24 PASS. A rerun against the current evidence-only worktree intentionally rejects `manuscript/Revision_Change_Map.md` and `manuscript/Final_Submission_Checklist.md`: authorized housekeeping H2 corrected the release-synchronization status, and the checklist now records GPT authorization and completed generation/QA work. These post-review documentation changes are not manuscript-science changes, and no self-validating commit loop was introduced.

## Remaining author-owned submission checks

- all authors confirm names, affiliations, funding, correspondence, and acknowledgements;
- the data owner approves the software/data availability wording;
- the corresponding author confirms Editorial Manager deadline and filename constraints.
