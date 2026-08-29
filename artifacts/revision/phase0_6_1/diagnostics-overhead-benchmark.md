# Phase 0.6.1 Alignment Diagnostics Overhead Benchmark

Scope: public sample common 16-step wide-table build with `164` mapped features.

| Mode | Median (ms) | P95 (ms) | Min (ms) | Max (ms) |
| --- | --- | --- | --- | --- |
| value_only | 641.918 | 757.406 | 583.636 | 781.641 |
| phase0_6_two_pass | 2199.344 | 2288.009 | 2079.917 | 2291.376 |
| phase0_6_1_one_pass | 1521.687 | 1650.707 | 1466.548 | 1669.28 |

- Maximum numerical difference across modes: `0.0`
- Two-pass and one-pass stage counts identical: `true`
- This is a local engineering microbenchmark, not a paper-level scalability claim.
