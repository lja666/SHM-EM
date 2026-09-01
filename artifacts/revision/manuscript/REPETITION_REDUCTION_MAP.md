# Repetition Reduction Map

The submitted manuscript repeatedly redefines the versioned data-model contract, Project Future State, and controlled forecast-to-event transition. The revision should assign one purpose to each section and use cross-references elsewhere.

| Manuscript location | Current role | Revision action | Content retained | Content removed or moved |
|---|---|---|---|---|
| Introduction | research gap and contribution list | Keep one compact contribution paragraph | one sentence per mechanism and the downstream relationship to Predictive-SHM | implementation sequence, repeated feature lists, and validation detail move to Sections 2 and 3 |
| Section 2.1 Software description | mechanism definition | Keep the only full technical explanation | contract fields/versioning; Future State algorithm/policy; Evaluate/Execute/Gate side-effect boundaries; provenance schema | broad impact claims and benchmark language move to Sections 3 and 4 |
| Section 2.2 Main functionalities | task-oriented feature overview | Compress to one short paragraph plus API/UI cross-references | observation/prediction query, prediction runs, rules/events, response/evidence entry points | redefinitions of the same three mechanisms and repeated architecture narrative |
| Section 3 Validation and examples | empirical evidence | Expand and make evidence primary | second configuration; failure matrix; runtime/scalability; testing summary; provenance trace; containerized workflow | generic statements that the architecture is reusable or safe without measurements |
| Section 4 Impact | consequences supported by Section 3 | Replace current prose with four evidence-driven subsections | reproducible validation; observed reuse effort; controlled execution/traceability; limitations | all mechanism redefinitions and absolute claims about any project, operational reliability, or portability |
| Conclusion | compact synthesis | Limit to one short paragraph | software scope, strongest validation result, and principal limitations | third repetition of the three mechanisms, new claims, and future-work detail |

## Contribution-specific ownership

| Contribution | Introduction | Section 2 | Section 3 | Section 4 | Conclusion |
|---|---|---|---|---|---|
| Versioned data-model contract | state contribution once | define and show compact contract | validate hashes, failure paths, and six-model configuration | state reproducibility consequence only | mention once in synthesis |
| Project Future State | state contribution once | define algorithm and deterministic policy | report boundary tests and runtime | state project-level decision-support consequence only | mention once in synthesis |
| Controlled transition | state contribution once | define Evaluate, Gate, Execute, and side effects | report 15-case matrix and provenance trace | state controlled-execution consequence only | mention once in synthesis |

## Space budget

- Remove approximately two paragraphs of repeated contribution prose from Section 2.2.
- Replace the current abstract Impact wording with the four evidence paragraphs in `IMPACT_RESTRUCTURING_PLAN.md`.
- Reduce Figure 4 from three pages to one compact composite.
- Use the recovered space for the contract example, algorithm, failure table, runtime table, reuse table, and provenance sequence.

The cover letter and final response will be rewritten in the final manuscript phase; they must summarize the revision rather than repeat the paper's mechanism definitions.
