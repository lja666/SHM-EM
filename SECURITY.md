# Security Policy

## Release Scope

SHM-EM is a research reference implementation. Version 1.0.1 does not provide
application-level authentication and does not claim production-grade
application security. Keep the public reproduction on an isolated host and do
not expose its API or MySQL service to an untrusted network.

Do not publish database passwords, API tokens, map keys, mail credentials, or
monitoring data without redistribution approval. Runtime secrets are accepted
only through environment variables, a deployment secret manager, or untracked
local configuration. The supplied Compose workflow binds web ports to
`127.0.0.1`, generates or requires reproduction-only credentials, and disables
notification delivery.

## Production Deployment Guidance

A production operator is responsible for adding controls outside this research
release:

- terminate TLS/HTTPS at a maintained reverse proxy or API gateway;
- use OIDC/OAuth2 or an equivalent identity provider;
- enforce role-based access control, with separate authorization for
  prediction `Execute` and administrative actions;
- use a least-privilege MySQL account and separate read/write roles where
  practical; never expose the database directly to clients;
- inject secrets through a secret manager or protected environment and rotate
  them independently of application releases;
- segment frontend, API, model-runner, database, and notification networks;
- protect audit/provenance storage from application-writer administration;
- define tested backup, restore, retention, and disaster-recovery procedures;
- apply rate limiting, request-size limits, and gateway logging to exposed APIs;
- keep notification integrations disabled or sandboxed in reproduction and
  test environments.

## Integrity Boundary

The persisted SHA-256 contracts detect accidental corruption, stale hash
metadata, uncoordinated row mutation, and partial database mutation. They are
not tamper-proof against an attacker with permission to update both data rows
and stored hashes. A stronger deployment requires privilege separation plus a
keyed HMAC or digital signature and/or an externally protected append-only
audit store. Those controls are recommendations, not features implemented by
this release.

## Reporting

The 1.0.x release line receives security fixes. Report vulnerabilities through
the public repository's private security-advisory channel after publication,
or through the corresponding author before the repository is public.
