# SHM-EM Backend

The backend is a Java 8 Spring Boot 2.6 application with MyBatis and MySQL.

## Run

```powershell
$env:DB_URL = 'jdbc:mysql://localhost:3306/shm_em?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai'
$env:DB_USERNAME = 'shm_em'
$env:DB_PASSWORD = '<app-password>'
mvn spring-boot:run
```

The API listens on `5101` by default. OpenAPI UI is available at
`/swagger-ui/index.html`.

## Test

```powershell
mvn clean test
```

The tests cover API contracts, observation routing, engineering conversion,
unified rule evaluation, prediction completeness and gates, future-state
aggregation, and notification policy.

## Runtime Policy

- Database credentials are required through environment variables.
- Notification scheduling and SMTP delivery are disabled in the release
  profile.
- APIs do not issue DDL.
- Project rules use `/api/em/projects/{projectId}/rules`.
- Project events use `/api/em/projects/{projectId}/events`.
- Event state actions remain under `/api/em/events/{eventId}`.
- Authentication is not built into release 1.0.1; secure deployments must
  enforce it at the infrastructure boundary.

See `docs/ARCHITECTURE.md` and `docs/API.md` in the repository root.
