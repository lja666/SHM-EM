# Figure 4 Reduction Plan

## Problem in the submitted manuscript

Submitted Figure 4 occupies three consecutive PDF pages (PDF pages 8-10; printed pages 7-9) with full-page screenshots of Project Workspace, Observation and Prediction, and Prediction Runs. Persistent navigation, headers, filters, and empty table areas dominate the area while evidence-bearing details become too small to read. The figure illustrates the interface but does not constitute scientific validation.

## Revised composition

Replace the three pages with one landscape compact composite, approximately 175 mm wide and 95-105 mm high:

| Panel | Relative area | Keep | Remove |
|---|---:|---|---|
| (a) Project Workspace | 40% | observed/forecast risk cards, site map risk symbols, earliest predicted exceedance | sidebar, global header, lower event inventory, decorative whitespace |
| (b) Observation and Prediction | 35% | shared observed/forecast timeline, base time, first exceedance marker, engineering unit, batch badge | object tree, large filter toolbar, raw table, secondary rate chart |
| (c) Prediction Runs | 25% | batch identity, six-model/124-target/40-step completeness, Gate eligibility/blocker state | sidebar, empty batch-table body, duplicate KPI cards, action buttons |

Use a 2-by-2 asymmetric layout: panel (a) spans the left column; panels (b) and (c) are stacked on the right. The curve in panel (b) must remain at least 85 mm wide in the final print layout. Add simple `(a)`, `(b)`, `(c)` labels outside the screenshots. Do not add explanatory callouts inside the UI.

## Capture and production specification

- Re-capture each crop at 2x device scale or higher from the same release and reference dataset.
- Export each source crop as lossless PNG; assemble the composite in a vector document so resizing does not resample text more than once.
- Target at least 300 dpi at final print dimensions and verify that the smallest retained UI label is readable at 100% PDF zoom.
- Keep the observed line, forecast line, base-time marker, Gate state, and all engineering units visible.
- Remove private project identifiers and any non-English labels before capture.
- Preserve source crops and the editable composite separately from the manuscript PDF.

## Caption boundary

Suggested caption: **Task-oriented interface views of SHM-EM: (a) project-level observed and forecast risk, (b) a joint engineering-valued observation/forecast series, and (c) prediction-batch completeness and execution eligibility. The interface is illustrative; quantitative validation is reported in the contract, failure-path, runtime, reuse, and provenance evidence.**

## Reallocated manuscript space

Use the recovered space for the compact data-model contract, Project Future State algorithm, 15-case failure matrix, runtime table, second-configuration reuse table, and one provenance trace. This directly addresses the reviewer's concern that screenshots should not substitute for scientific evidence.
