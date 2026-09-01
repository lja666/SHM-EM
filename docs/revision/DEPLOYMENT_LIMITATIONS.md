# Deployment and Forecast Limitations

- SHM-EM is a research reference implementation and has no built-in user
  authentication or production authorization subsystem.
- Docker Compose demonstrates isolated reproducibility; it is not a hardened
  production topology. Production controls are listed in `SECURITY.md`.
- Persisted SHA-256 checks detect integrity inconsistencies but do not prevent
  a privileged database attacker from changing both rows and stored hashes.
- The current reference models produce point forecasts. Gate validity verifies
  contract, completeness, integrity, quality, and freshness; it is not a
  forecast-uncertainty confidence statement.
- Forecast output must not be the sole basis for automated safety decisions.
  Interval, quantile, or probabilistic-exceedance models remain future work.
- Only the MySQL storage implementation is validated. The documented storage
  boundary does not establish conformance for another database.
- The current Gate inspection cap of 50,000 rows is an implementation boundary,
  not a database capacity result or a general scalability limit.
