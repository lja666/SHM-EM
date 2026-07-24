# SHM-EM Frontend

The Vue 3 frontend presents the forecast-driven monitoring workflow through seven
project-scoped views:

| View | Route |
|---|---|
| Project Catalog | `/projects` |
| Project Workspace | `/projects/:projectId/overview` |
| Object Topology | `/projects/:projectId/topology` |
| Observation & Prediction | `/projects/:projectId/data/low-frequency` |
| Prediction Runs | `/projects/:projectId/predictions` |
| Rules & Events | `/projects/:projectId/events` |
| Response & Evidence | `/projects/:projectId/response/workflows` |

## Development

```powershell
npm ci
npm run dev
```

The Vite development proxy targets `http://localhost:5101` by default.
Override it only when the backend uses another origin:

```text
VITE_API_BASE_URL=http://localhost:5101
```

Optional AMap configuration:

```text
VITE_AMAP_KEY=<web-js-api-key>
VITE_AMAP_SECURITY_JS_CODE=<security-code>
```

Keep keys in `.env.local` or deployment secrets. With no key, the project
catalog shows a neutral no-map state.

## Build

```powershell
npm run typecheck
npm run build
```

Deploy the generated `dist` directory with any static web server and route
`/api` to the backend service when using same-origin deployment.

## UI Contracts

- All visible application text is English.
- Project pages use project-scoped APIs.
- Observation queries use registry codes and never physical table names.
- Charts consume engineering-value `MetricSeriesPoint` records.
- Opening a chart does not trigger model inference.
- The UI displays observed and forecast risk separately.
- The UI does not invent confidence intervals, data-health percentages, or
  other unavailable scientific values.
