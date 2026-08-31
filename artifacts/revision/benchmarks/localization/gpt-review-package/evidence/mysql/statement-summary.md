# MySQL Runtime Statement Summary

`SHOW FULL PROCESSLIST` was sampled throughout every long Gate call. The Gate connection remained in `Query: executing` on the prediction-display SQL through the 180-second boundary.

Performance Schema statement consumers were available, but the server-wide digest table contained 10000 of 10000 rows and was saturated before this run. No matching scaling-schema digest was retained. Therefore, digest aggregates are marked unavailable; runtime processlist, direct query timing, and `EXPLAIN ANALYZE` are the authoritative SQL evidence.
