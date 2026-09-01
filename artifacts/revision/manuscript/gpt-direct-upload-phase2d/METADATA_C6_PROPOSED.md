# Metadata C6 Proposed Wording

## Full version

Back end: Java 8 and Maven 3.8+; database: MySQL 8.0+; front end: Node.js 20+ and npm; forecasting runtime: Python 3.10 with locked dependencies. Exact reference-output reproduction was validated on Windows 10/11 with PowerShell 7. The revision additionally provides and exercises a Docker Compose Linux workflow for database initialization, component checks, six-model inference, Gate, Project Future State, Evaluate, Execute, and provenance. The Linux container run matched the reference input/model contracts and workflow semantics but did not produce a bitwise-identical normalized prediction-output hash.

## Compact metadata-cell version

Java 8/Maven 3.8+, MySQL 8.0+, Node.js 20+/npm, and Python 3.10 with locked dependencies. Windows 10/11 + PowerShell 7 is the exact-output reference. An exercised Docker Compose Linux workflow reproduces component checks and the logical six-model-to-provenance path; input/model contracts match, but the normalized prediction-output hash is not bitwise identical.

## Required accompanying limitation

The Docker run reproduced six models, 124 targets, 40 steps, and 4,960 persisted rows with complete Gate, Future State, Evaluate, Execute, and provenance semantics. Its normalized output hash differed from the Windows reference (`exactPredictionReproduction=false`); maximum persisted absolute difference was `0.00285349`, maximum relative difference was `0.3918730158730158730158730159`, and no tolerance was applied (`toleranceApplied=false`). The full row-wise comparison artifact is retained in the repository. Native Ubuntu-host validation was not separately captured.
