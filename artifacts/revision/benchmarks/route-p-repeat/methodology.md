# Phase 2A.2R Controlled Contemporaneous A/B Repeat

- Variant A: clean detached worktree at `84c13fa6081f72b37483b475903c7b22e1a8b92d`.
- Variant B: current uncommitted Route P working tree with exactly one production assignment.
- Reference order: A-B, B-A, A-B, B-A; each fresh process uses 3 warmups and 15 measured calls.
- Phase 1B and S1 order: A-B, B-A; fresh process for every variant/block.
- Same JDK, Maven, MySQL server, database snapshot, machine, JVM profile, and Gate endpoint.
