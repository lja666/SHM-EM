# Storage Adapter Boundary

## Purpose

This document states what is logically portable in SHM-EM, what is implemented
specifically for MySQL, and what must be supplied by a future time-series
database adapter. It is an architectural extension boundary, not a claim that
multiple databases have been validated.

## Layer 1: Logical Observation Contract

The stable engineering vocabulary is:

```text
project -> station -> instrument -> metric -> timestamped observation
```

An observation carries device-native and engineering values, units, quality,
collection time, source identity, conversion operator/version/status, and the
conversion parameter snapshot. Rule evaluation consumes the common
`MetricSeriesPoint` representation for either observations or predictions.
Frontend and API clients select logical registry/metric codes and never submit
a physical table name.

## Layer 2: Approved Observation Adapters

The current release routes low-frequency reads through
`ObservationRoutingService`, `LowFrequencyObservationService`, and the
allowlisted `em_observation_table_registry`. The registry is validated for
enabled/queryable state, storage mode, and a safe table identifier before the
MyBatis mapper executes a query. Supported physical forms are the four typed
`em_obs_*` tables and the two intentionally retained acceleration sensor
tables documented in `docs/DATABASE.md`.

PIT_PRE uses the same registered project/station/instrument/metric mappings to
assemble its ordered model inputs. Registration does not mean that an
arbitrary table schema is automatically supported: its columns, time
semantics, units, and engineering conversion must satisfy the approved adapter
contract.

## Layer 3: MySQL Implementation

The following are currently MySQL-specific:

- schema DDL, views, generated SQL validation, JSON extraction, and collation;
- JDBC connection semantics and MyBatis mapper SQL;
- registry resolution to MySQL physical table names;
- PIT_PRE PyMySQL queries and transaction behavior;
- database initialization and integrity queries used by reproduction scripts.

MySQL 8.4 is the validated database for the reference workflow. The Gate's
50,000 display-row inspection limit is an application boundary, not a MySQL
capacity limit. Evidence covers the 4,960-row reference and a 49,600-row
synthetic functional stress case; it does not establish linear scalability.

## Alternative Adapter Responsibilities

A TimescaleDB, InfluxDB, or other time-series integration would need to:

1. resolve logical project/station/instrument/metric identifiers without
   exposing untrusted physical identifiers;
2. return deterministic timestamp ordering and explicit time-zone semantics;
3. preserve raw and engineering values, units, quality, and conversion
   provenance;
4. implement the query/filter/pagination behavior required by
   `LowFrequencyObservationService` and `MetricSeriesProvider`;
5. supply PIT_PRE input assembly with the same canonical alignment contract;
6. preserve transaction and persisted-integrity semantics for prediction,
   Gate, event, and provenance records, or retain MySQL for that write model;
7. pass contract, conversion, rule, provenance, and cross-language hash tests.

No alternative adapter or SensorThings conformance layer is implemented or
validated in SHM-EM 1.0.1.
