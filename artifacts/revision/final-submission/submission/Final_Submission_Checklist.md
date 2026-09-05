# Final Submission Checklist

This checklist separates completed source/evidence work from tasks that must wait until GPT scientific-consistency approval and final document generation.

## A. Scientific source preflight

- [x] Submitted Editorial Manager PDF used as the authoritative baseline.
- [x] Exactly three contributions retained.
- [x] M1: Predictive-SHM shared origin/future timeline changed from `Partial` to `Not reported`.
- [x] M2: validation matrix consistently described as 1 positive + 12 failure + 2 input controls.
- [x] M3: two second-configuration bundles explicitly limited to software-workflow fixtures.
- [x] M4: Docker output-hash mismatch, no tolerance, and row-wise artifact retained.
- [x] Six models, 124 targets, 40 steps, and 4,960 reference rows used consistently.
- [x] Common source window 16 steps and model-specific histories 12-16 steps distinguished.
- [x] Frozen aligned input/output widths reconciled as 114/42, 114/42, 114/14, 114/14, 114/2, and 164/10; database mapping counts are labelled separately.
- [x] Pressure's 13-row runner window and 12-row (`m+lag`) scaled model window are distinguished.
- [x] Evaluate audit persistence is explicit; unqualified “side-effect-free Evaluate” is removed.
- [x] Generic CEP execution recheck and event-to-prediction provenance cells are `Not reported`.
- [x] SensorThings reference [8] uses Part 1 Sensing v1.1, OGC 18-088.
- [x] Gate reference median/p95 fixed at 343.129/407.100 ms.
- [x] S1/S2 fixed at 4,960/49,600 rows and described as bounded endpoints.
- [x] 50,000 rows described as a Gate application cap, not a MySQL limit.
- [x] Point-forecast, MySQL-only, no alternative TSDB, no SensorThings conformance, research-security, and adapter-scope limitations retained.

## B. Reviewer-response coverage

- [x] Reviewer 1 general comment and R1-1 through R1-19 answered.
- [x] Reviewer 2 R2-1 through R2-3 answered.
- [x] Reviewer 3 R3-1 through R3-4 answered.
- [x] Every response includes comment, response, manuscript change, evidence, and scope/non-claim.
- [x] Reviewer 2 accuracy response explains why software evidence replaces an inappropriate forecasting-accuracy comparison.
- [x] F09 persisted-integrity discovery and narrow correction explained.
- [x] Docker response states functional/logical E2E, normalized hash mismatch, and no tolerance.

## C. Repository/evidence boundary

- [x] Final Core Freeze v3 recorded as `eaa7d85a0b4921ab2f6e54234cff09aee6a30c8f`.
- [x] Production-core diff remains empty for `src/backend/src/main`, `src/pit_pre/pit_pre`, and `src/frontend/src`.
- [x] No new model, experiment, performance optimization, tolerance, SensorThings adapter, authentication subsystem, or third configuration added in the manuscript phase.
- [x] Full row-wise Windows/Linux difference artifact retained.
- [x] Review files stored under project-local paths.

## D. Required GPT stop/review

- [x] GPT confirms manuscript claims match repository evidence.
- [x] GPT confirms contribution novelty and related-software language are scientifically fair.
- [x] GPT confirms all reviewer comments are answered without overclaiming.
- [x] GPT confirms table/figure numbering and proposed structure are coherent.
- [x] GPT authorizes final DOCX generation.

## E. After GPT approval only

- [x] Render revised Fig. 3 from the code-crosschecked Mermaid source.
- [x] Produce the compact three-panel Fig. 4 at publication resolution.
- [x] Correct Fig. 5 model dimensions/labels.
- [x] Generate `Revised Manuscript Clean.docx`.
- [x] Generate `Revised Manuscript Marked.docx` against the submitted PDF text baseline.
- [x] Generate `Response to Reviewers.docx` with final page/line references.
- [x] Render all DOCX files to PDF/PNG and inspect every page for overflow, broken tables, image clarity, and reference formatting.

## F. Public-release synchronization before submission

- [x] Push Final Core Freeze v3 and manuscript/revision documentation to the public repository.
- [x] Create immutable revision tag `v1.0.1` without moving submitted tag `v1.0.0`; make C1/C2/C7 consistent.
- [x] Ensure the fixed commit in metadata is publicly reachable.
- [x] Rebuild the public release archive from the immutable release commit.
- [x] Recalculate and insert the final release SHA-256 in Section 6 and repository documentation.
- [x] Confirm public sample and conceptual site plan carry CC BY 4.0 notices.
- [x] Confirm source code and model bundles carry MIT notices.
- [x] Confirm no private field data, credentials, map keys, operational identifiers, generated local database files, or manuscript working files occur in the release archive.
- [x] Verify release, archive, checksum, repository, documentation, and cited DOI/standard URLs used by the final sources.

## G. Editorial submission package

- [x] Clean revised manuscript.
- [x] Marked revised manuscript.
- [x] Point-by-point response letter.
- [x] Revised Fig. 1-Fig. 5 as separate editable auxiliaries and PDF/TIFF submission artwork.
- [x] Updated metadata table and declaration statements.
- [ ] Final author names, affiliations, funding numbers, corresponding email, and acknowledgements checked by all authors.
- [ ] Software/data availability wording approved by the data owner.
- [ ] Submission deadline and Editorial Manager file naming requirements checked.

## H. SoftwareX final compliance gates

- [x] FS-01 SOFTWAREX_WORD_COUNT: strict count is at most 3000 and targets at most 2900.
- [x] FS-02 FIGURE_COUNT: five figures, below the six-figure maximum.
- [x] FS-03 AI_DECLARATION_PRESENT: Elsevier declaration is immediately before References.
- [x] FS-04 COMPLETE_ARTWORK_SET: separate Fig. 1-Fig. 5 submission files are generated.
- [x] FS-05 ARTWORK_FORMAT: Fig. 1-Fig. 3 PDF; Fig. 4-Fig. 5 TIFF at at least 500 dpi.
- [x] FS-06 RESPONSE_PAGE_LINE_REFERENCES: all 27 locations are recomputed from the final clean manuscript.
- [ ] FS-07A COMPETING_INTEREST_CONFIRMED: corresponding author confirmation is required.
- [ ] FS-07B CRediT_ROLES_CONFIRMED: all authors must confirm their actual roles.
- [ ] FS-08 FINAL_AUTHOR_CHECK: all authors must confirm identity, funding, funding-role wording, correspondence, and acknowledgements.
- [ ] FS-09 DATA_OWNER_CHECK: data owner approval remains required.
- [ ] FS-10 EM_UPLOAD_CHECK: final deadline, item types, and filenames remain to be checked.
- [x] FS-11 AI_FIGURE_DISCLOSURE: figure provenance, caption-level disclosures, and the general declaration are complete.
- [x] FS-12 AI_CODE_METHOD_DISCLOSURE: Section 3.5 records revision-stage AI-assisted code editing and human/regression review.
- [x] FS-13 POST_AI_WORDCOUNT: the regenerated clean manuscript remains within the 3000-word limit.
- [x] FS-14 POST_AI_PAGE_LINE_MAP: all 27 locations are regenerated and verified after the disclosure edits.
