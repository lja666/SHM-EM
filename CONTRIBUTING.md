# Contributing

Contributions should preserve SHM-EM's traceable engineering-monitoring
contracts.

Before submitting a change:

1. Run `mvn clean test` in `src/backend`.
2. Run `npm run build` in `src/frontend`.
3. Run `python -m unittest discover -s tests -v` in `src/pit_pre`.
4. Keep model paths, hashes, feature order, cadence, and horizon in the database
   contract; do not add them to local JSON.
5. Preserve immutable raw values and version every engineering conversion.
6. Keep frontend labels in English and do not invent values for unavailable
   scientific measurements.
7. Do not commit credentials, local environment files, IDE metadata, build
   output, logs, or runtime prediction CSV files.

Changes to data, model contracts, conversion formulas, or expected hashes must
also update `docs/REPRODUCIBILITY.md` and the release validation baseline.

