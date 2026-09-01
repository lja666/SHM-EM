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
- [x] Model-specific input/target widths corrected to 42/42, 42/42, 14/14, 14/14, 2/2, and 50/10.
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

- [ ] GPT confirms manuscript claims match repository evidence.
- [ ] GPT confirms contribution novelty and related-software language are scientifically fair.
- [ ] GPT confirms all reviewer comments are answered without overclaiming.
- [ ] GPT confirms table/figure numbering and proposed structure are coherent.
- [ ] GPT authorizes final DOCX generation.

## E. After GPT approval only

- [ ] Render revised Fig. 3 from the code-crosschecked Mermaid source.
- [ ] Produce the compact three-panel Fig. 4 at publication resolution.
- [ ] Correct Fig. 5 model dimensions/labels.
- [ ] Generate `Revised Manuscript Clean.docx`.
- [ ] Generate `Revised Manuscript Marked.docx` against the submitted PDF text baseline.
- [ ] Generate `Response to Reviewers.docx` with final page/line references.
- [ ] Render all DOCX files to PDF/PNG and inspect every page for overflow, broken tables, image clarity, and reference formatting.

## F. Public-release synchronization before submission

- [ ] Push Final Core Freeze v3 and manuscript/revision documentation to the public repository.
- [ ] Decide whether to retain tag `v1.0.0` or create a revision release; make C1/C2/C7 consistent with that decision.
- [ ] Ensure the fixed commit in metadata is publicly reachable.
- [ ] Rebuild the public release archive from the final authorized commit.
- [ ] Recalculate and insert the final release SHA-256 in Section 6 and repository documentation.
- [ ] Confirm public sample and conceptual site plan carry CC BY 4.0 notices.
- [ ] Confirm source code and model bundles carry MIT notices.
- [ ] Confirm no private field data, credentials, map keys, operational identifiers, or generated local database files are tracked.
- [ ] Verify every URL in metadata, data availability, citations, and reviewer evidence.

## G. Editorial submission package

- [ ] Clean revised manuscript.
- [ ] Marked revised manuscript.
- [ ] Point-by-point response letter.
- [ ] Revised figures as separate high-resolution files if required.
- [ ] Updated metadata table and declaration statements.
- [ ] Final author names, affiliations, funding numbers, corresponding email, and acknowledgements checked by all authors.
- [ ] Software/data availability wording approved by the data owner.
- [ ] Submission deadline and Editorial Manager file naming requirements checked.
