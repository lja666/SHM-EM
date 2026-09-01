# OGC SensorThings Positioning

## Standards boundary

OGC SensorThings API Part 1: Sensing 1.1 provides an open, geospatially enabled interface for managing and retrieving observations and metadata from heterogeneous IoT sensor systems. Its sensing model includes Thing, Location, Datastream, Sensor, ObservedProperty, Observation, and FeatureOfInterest resources. A conformance claim requires the relevant normative Annex A tests.

SHM-EM v1.0.0 does **not** implement a SensorThings API endpoint, a SensorThings ingestion adapter, or the OGC conformance tests. It therefore makes no claim of SensorThings API conformance or compatibility.

## Relationship to SHM-EM

SHM-EM's observation registry is an internal engineering/data-source abstraction. It resolves approved physical observation tables through registered metadata and exposes canonical engineering-valued metric series to downstream services. A future SensorThings adapter could map SensorThings resources as follows:

| SensorThings resource | Possible SHM-EM registry role |
|---|---|
| Thing / FeatureOfInterest | project, station, or monitored-object identity |
| Sensor | instrument identity and type |
| ObservedProperty | metric code and engineering unit |
| Datastream | registered observation source and cadence |
| Observation | timestamped raw/engineering value plus quality metadata |

This mapping is a prospective adapter boundary, not an implemented feature. SHM-EM's versioned model-specific feature ordering, model artifacts, persisted forecast batches, execution Gate, Project Future State, Evaluate/Execute separation, and formal event provenance operate downstream of the observation interface and are outside SensorThings Sensing's stated responsibility.

## Manuscript-ready wording

> OGC SensorThings standardizes observation and sensor-resource access. SHM-EM's observation registry is a separate internal engineering/data-source abstraction. A SensorThings ingestion adapter could map compliant observations into that registry, but no SensorThings API conformance is implemented or claimed in the current release. SHM-EM's model-specific data contract and forecast-to-event controls operate downstream of the observation interface.

Source: [OGC SensorThings API Part 1: Sensing Version 1.1](https://docs.ogc.org/is/18-088/18-088.html), accessed 2026-09-01.
