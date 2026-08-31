# JVM and Thread Diagnostic Summary

- Request-thread samples: 114.
- Dominant category: `jdbc-mysql-read` (114 samples).
- Timeout scenarios: 10.
- Timeout processlist samples with an active query: 2571 / 2586.
- Maximum observed RSS: 1751265280 bytes.
- Maximum observed GC-time increase during a sampled Gate interval: 0.000000 seconds.

All sampled Gate request threads remained in the MySQL read path. No sample reached feature/timeline validation, canonical hashing, persisted integrity hashing, or response serialization. GC counters were stable during the long Gate intervals, including the high-RSS D03/D04 processes.
