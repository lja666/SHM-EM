# API Guide

The backend listens on port 5101 by default. All responses use
`{"code": 0, "message": "success", "data": ...}` on success. Live OpenAPI
documentation is available at `/swagger-ui/index.html`.

## Project and Object Context

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/em/projects` | List projects |
| GET | `/api/em/projects/{id}` | Project summary |
| GET | `/api/em/projects/{id}/context` | Settings and distribution facts |
| GET | `/api/em/projects/{id}/object-tree` | Stations, instruments, and metrics |
| GET | `/api/em/projects/{id}/future-state` | Observed and forecast project risk |

## Observation and Prediction

| Method | Route | Purpose |
|---|---|---|
| GET/POST | `/api/em/observations/low-frequency` or `/query` | Typed observation query |
| POST | `/api/em/observations/low-frequency/timeseries` | Engineering-value series |
| GET/POST | `/api/em/acceleration` or `/waveform` | Acceleration query |
| GET | `/api/em/predictions/batches` | Prediction batches |
| GET | `/api/em/predictions/batches/{batchId}` | Batch detail and completeness |
| GET | `/api/em/predictions/batches/{batchId}/runs` | Six model runs |
| GET | `/api/em/predictions/series` | Unified observed/forecast series |
| GET | `/api/em/predictions/batches/{batchId}/execution-gate` | Inspect a gate decision |
| POST | `/api/em/predictions/batches/{batchId}/execution-gate/evaluate` | Persist a gate decision |
| GET | `/api/em/predictions/events/{eventId}/trace` | Event-to-prediction evidence |

## Rules, Events, and Response

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/em/projects/{projectId}/rules` | Project rule catalog |
| POST | `/api/em/projects/{projectId}/rules/evaluate` | Side-effect-free custom evaluation |
| POST | `/api/em/projects/{projectId}/rules/execute` | Execute a custom rule |
| POST | `/api/em/projects/{projectId}/rules/{ruleId}/evaluate` | Evaluate a stored rule |
| POST | `/api/em/projects/{projectId}/rules/{ruleId}/execute` | Execute a stored rule |
| GET | `/api/em/projects/{projectId}/events` | Project event queue |
| GET/POST | `/api/em/events/{id}` and action suffixes | Event detail and state actions |
| GET | `/api/em/event-response-workflows` | Response workflow |
| GET | `/api/em/notification-tasks` | Notification tasks |
| GET | `/api/em/reports` | Generated reports |
| GET | `/api/em/evidence` | Generic evidence attachments |

`Evaluate` does not create events. Forecast `Execute` requires an eligible
`OPERATIONAL` gate and writes the event-prediction link with the formal event.
Query fields and request schemas should be inspected in OpenAPI because they
are versioned with the code.
